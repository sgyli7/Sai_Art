#include <godot_cpp/godot.hpp>
#include <godot_cpp/classes/ref_counted.hpp>
#include <godot_cpp/classes/rigid_body3d.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/dictionary.hpp>
#include <godot_cpp/variant/packed_vector4_array.hpp>
#include <godot_cpp/variant/vector2.hpp>
#include <godot_cpp/variant/vector3.hpp>
#include <algorithm>
#include <array>
#include <cmath>
#include <vector>
using namespace godot;
// Track geometry and read-only contact sampling. No force, time decimation or pose writes.
class LeviathanTrackPath : public RefCounted {
    GDCLASS(LeviathanTrackPath,RefCounted)
protected:
    static void _bind_methods() {
        ClassDB::bind_method(D_METHOD("build","wheels","travel","idler"),&LeviathanTrackPath::build);
        ClassDB::bind_method(D_METHOD("envelope","wheels"),&LeviathanTrackPath::envelope);
        ClassDB::bind_method(D_METHOD("contact_geometry","contacts","terrain","offset_x","offset_z","max_factor"),&LeviathanTrackPath::contact_geometry);
        ClassDB::bind_method(D_METHOD("sample_linear_links","links"),&LeviathanTrackPath::sample_linear_links);
    }
public:
    // Read the existing dynamic links in one native call. The returned states
    // are the same values the GDScript force controller consumes; no pose or
    // force is changed here.
    Dictionary sample_linear_links(Array links) const {
        Array coordinates,rates;
        for(int i=0;i<links.size();++i){
            Dictionary link=links[i];
            Object *parent_object=link["parent"],*body_object=link["body"];
            RigidBody3D *parent=Object::cast_to<RigidBody3D>(parent_object);
            RigidBody3D *body=Object::cast_to<RigidBody3D>(body_object);
            ERR_FAIL_NULL_V(parent,Dictionary());
            ERR_FAIL_NULL_V(body,Dictionary());
            const Transform3D pt=parent->get_global_transform(),bt=body->get_global_transform();
            const Vector3 axis=pt.basis.xform(Vector3(link["axis"]));
            const Vector3 pa=pt.xform(Vector3(link["a"])),pb=bt.xform(Vector3(link["b"]));
            const Vector3 parent_com=pt.xform(parent->get_center_of_mass()),body_com=bt.xform(body->get_center_of_mass());
            const Vector3 parent_velocity=parent->get_linear_velocity()+parent->get_angular_velocity().cross(pa-parent_com);
            const Vector3 body_velocity=body->get_linear_velocity()+body->get_angular_velocity().cross(pb-body_com);
            const double q=(pb-pa).dot(axis),dq=(body_velocity-parent_velocity).dot(axis);
            Array state;state.push_back(axis);state.push_back(pa);state.push_back(pb);state.push_back(q);state.push_back(dq);
            link["control_state"]=state;
            coordinates.push_back(q);rates.push_back(dq);
        }
        Dictionary out;out["coordinates"]=coordinates;out["rates"]=rates;return out;
    }
    static double bump(double x,double center,double width,double height){
        constexpr double pi=3.1415926535897932384626433832795;
        return height*0.5*(1.0+std::cos(pi*std::clamp((x-center)/width,-1.0,1.0)));
    }
    static double ground_height(const String &terrain,double x,double y){
        if(terrain=="flat")return 0.0;
        constexpr double tau=6.283185307179586476925286766559;
        const double hill=bump(x,85.0,75.0,1.8)*bump(y,0.0,150.0,1.0);
        const double window=std::clamp((x-10.0)/14.0,0.0,1.0)*std::clamp((180.0-x)/14.0,0.0,1.0);
        return hill+window*bump(y,0.0,150.0,1.0)*(.09*std::sin(tau*x/17.0)+.06*std::sin(tau*x/9.0+std::tanh(y/8.0))+.05*std::sin(y/13.0));
    }
    Dictionary contact_geometry(Array contacts,String terrain,double offset_x,double offset_z,double max_factor) const {
        Dictionary result;
        if(terrain!="flat"&&terrain!="polar")return result;
        double total_load=0.0;int supported=0;
        for(int i=0;i<contacts.size();++i){
            Dictionary item=contacts[i];Object *object=item["body"];
            RigidBody3D *body=Object::cast_to<RigidBody3D>(object);
            ERR_FAIL_NULL_V(body,Dictionary());
            const Transform3D transform=body->get_global_transform();
            const Vector3 center=transform.xform(Vector3(item["local"]));
            const double wx=double(center.x)+offset_x,wy=-double(center.z)-offset_z;
            const double h=ground_height(terrain,wx,wy);
            const double dx=(ground_height(terrain,wx+.01,wy)-ground_height(terrain,wx-.01,wy))/.02;
            const double dy=(ground_height(terrain,wx,wy+.01)-ground_height(terrain,wx,wy-.01))/.02;
            const Vector3 normal=Vector3(-dx,1.0,dy).normalized();
            const double radius=item["radius"];
            const double penetration=radius-(double(center.y)-h)*double(normal.y);
            const Vector3 point=center-normal*radius;
            const Vector3 velocity=body->get_linear_velocity()+body->get_angular_velocity().cross(point-transform.xform(body->get_center_of_mass()));
            const double stiffness=item["stiffness"],damping=item["damping"],nominal=item["nominal"];
            const double load=penetration>=0.0?std::clamp(stiffness*penetration-damping*double(velocity.dot(normal)),0.0,nominal*max_factor):0.0;
            const Vector3 axis=transform.basis.get_column(0);
            const Vector3 forward=(axis-normal*axis.dot(normal)).normalized();
            const Vector3 lateral=normal.cross(forward);
            const double speed=velocity.dot(forward);
            item["point"]=point;item["normal"]=normal;item["forward"]=forward;item["lateral"]=lateral;
            item["velocity"]=velocity;item["load"]=load;item["speed"]=speed;
            total_load+=load;if(load>1.0)++supported;
        }
        result["total_load"]=total_load;result["supported"]=supported;return result;
    }
    Dictionary envelope(Array wheels) const {
        constexpr double tau=6.283185307179586476925286766559;
        const int count=wheels.size();
        std::vector<Vector3> w;w.reserve(count);
        for(int i=0;i<count;++i)w.push_back(wheels[i]);
        std::vector<double> angles{0.0,tau};angles.reserve(2+count*(count-1));
        auto mod=[](double x,double m){double r=std::fmod(x,m);return r<0?r+m:r;};
        for(int i=0;i<count;++i)for(int j=0;j<i;++j){
            const double dx=double(w[i].x)-double(w[j].x),dz=double(w[i].y)-double(w[j].y);
            const double distance=std::sqrt(dx*dx+dz*dz);
            if(distance<=std::abs(double(w[j].z)-double(w[i].z)))continue;
            const double a=std::atan2(dz,dx),b=std::acos((double(w[j].z)-double(w[i].z))/distance);
            angles.push_back(mod(a-b,tau));angles.push_back(mod(a+b,tau));
        }
        std::sort(angles.begin(),angles.end());
        std::vector<Vector2> gradient(count,Vector2());
        double length=0.0;
        for(size_t k=0;k+1<angles.size();++k){
            const double a=angles[k],b=angles[k+1];
            if(b-a<1e-12)continue;
            const double mid=(a+b)*0.5,nx=std::cos(mid),nz=std::sin(mid);
            int owner=0;double support=-INFINITY;
            for(int i=0;i<count;++i){
                const double value=double(w[i].x)*nx+double(w[i].y)*nz+double(w[i].z);
                if(value>support){support=value;owner=i;}
            }
            const Vector2 integral(std::sin(b)-std::sin(a),std::cos(a)-std::cos(b));
            gradient[owner]+=integral;
            length+=double(w[owner].x)*integral.x+double(w[owner].y)*integral.y+double(w[owner].z)*(b-a);
        }
        Array result_gradient;
        for(const Vector2 &value:gradient)result_gradient.push_back(value);
        Dictionary result;result["length"]=length;result["gradient"]=result_gradient;
        return result;
    }
    Dictionary build(Array wheels,Vector3 travel,double idler) const {
        ERR_FAIL_COND_V(wheels.size()!=5,Dictionary());
        constexpr double pi=3.1415926535897932384626433832795,tau=2*pi;
        std::array<Vector3,5> w;
        for(int i=0;i<5;++i) {Array v=wheels[i];ERR_FAIL_COND_V(v.size()!=3,Dictionary());w[i]=Vector3(double(v[0]),double(v[1]),double(v[2])+.09);}
        for(int i=0;i<3;++i)w[i+1].y+=travel[i];
        w[4].x+=idler;
        const double upper=pi*.5,lower=upper-tau;
        std::vector<double> angles{upper,lower};angles.reserve(22);
        auto mod=[](double x,double m){double r=std::fmod(x,m);return r<0?r+m:r;};
        for(int i=0;i<5;++i)for(int j=0;j<i;++j) {
            const double dx=double(w[i].x)-double(w[j].x),dz=double(w[i].y)-double(w[j].y),distance=std::sqrt(dx*dx+dz*dz);
            if(distance<=std::abs(double(w[j].z)-double(w[i].z)))continue;
            const double a=std::atan2(dz,dx),b=std::acos((double(w[j].z)-double(w[i].z))/distance);
            angles.push_back(lower+mod(a-b-lower,tau));angles.push_back(lower+mod(a+b-lower,tau));
        }
        std::sort(angles.begin(),angles.end(),std::greater<double>());
        struct Arc {int owner;double start,end;};std::vector<Arc> arcs;arcs.reserve(6);
        for(size_t k=0;k+1<angles.size();++k) {
            const double a=angles[k],b=angles[k+1];if(a-b<1e-10)continue;
            const double mid=(a+b)*.5,nx=std::cos(mid),nz=std::sin(mid);int owner=0;double support=-INFINITY;
            for(int i=0;i<5;++i){const double value=w[i].x*nx+w[i].y*nz+w[i].z;if(value>support){owner=i;support=value;}}
            if(!arcs.empty()&&arcs.back().owner==owner)arcs.back().end=b;else arcs.push_back({owner,a,b});
        }
        PackedVector4Array first,second;double total=0;
        for(size_t i=0;i<arcs.size();++i) {
            const auto &arc=arcs[i],&previous=arcs[(i+arcs.size()-1)%arcs.size()];
            const Vector3 c=w[arc.owner],p=w[previous.owner];const Vector2 n(std::cos(arc.start),std::sin(arc.start));
            const Vector2 start=Vector2(p.x,p.y)+p.z*n,end=Vector2(c.x,c.y)+c.z*n;
            double length=start.distance_to(end);
            if(length>1e-8){first.push_back(Vector4(start.x,start.y,end.x,end.y));second.push_back(Vector4(length,0,0,0));total+=length;}
            length=c.z*(arc.start-arc.end);first.push_back(Vector4(c.x,c.y,c.z,arc.start));second.push_back(Vector4(length,arc.end-arc.start,1,0));total+=length;
        }
        ERR_FAIL_COND_V(first.size()>16,Dictionary());const int count=first.size();
        while(first.size()<16){first.push_back(Vector4());second.push_back(Vector4());}
        Dictionary out;out["a"]=first;out["b"]=second;out["length"]=total;out["count"]=count;return out;
    }
};
void initialize_path(ModuleInitializationLevel level){if(level==MODULE_INITIALIZATION_LEVEL_SCENE)ClassDB::register_class<LeviathanTrackPath>();}
void terminate_path(ModuleInitializationLevel){}
extern "C" GDExtensionBool GDE_EXPORT leviathan_track_path_init(GDExtensionInterfaceGetProcAddress get_proc,GDExtensionClassLibraryPtr library,GDExtensionInitialization *initialization){
    GDExtensionBinding::InitObject init(get_proc,library,initialization);init.register_initializer(initialize_path);init.register_terminator(terminate_path);init.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);return init.init();
}
