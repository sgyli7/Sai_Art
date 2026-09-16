#include <godot_cpp/godot.hpp>
#include <godot_cpp/classes/ref_counted.hpp>
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
// Pure display geometry. No physics access, force, time decimation or pose writes.
class LeviathanTrackPath : public RefCounted {
    GDCLASS(LeviathanTrackPath,RefCounted)
protected:
    static void _bind_methods() {ClassDB::bind_method(D_METHOD("build","wheels","travel","idler"),&LeviathanTrackPath::build);}
public:
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
