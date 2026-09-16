shader_type spatial;
render_mode cull_back, specular_disabled;
uniform vec4 paint:source_color=vec4(0.4,0.4,0.4,1.);
uniform float metal=.35;
uniform sampler2D track_state:filter_nearest,repeat_disable;
uniform int state_row;



const vec2 path[29]=vec2[](vec2(-4.15000000,3.37000000),vec2(4.15000000,3.37000000),vec2(4.40105450,3.33694810),vec2(4.63500000,3.24004460),vec2(4.83589360,3.08589360),vec2(4.99004460,2.88500000),vec2(5.08694810,2.65105450),vec2(5.12000000,2.40000000),vec2(5.08694810,2.14894550),vec2(4.99004460,1.91500000),vec2(4.83589360,1.71410640),vec2(4.63500000,1.55995540),vec2(2.99500000,0.37923740),vec2(2.78034900,0.29032600),vec2(2.55000000,0.26000000),vec2(-2.55000000,0.26000000),vec2(-2.78034900,0.29032600),vec2(-2.99500000,0.37923740),vec2(-4.63500000,1.55995540),vec2(-4.83589360,1.71410640),vec2(-4.99004460,1.91500000),vec2(-5.08694810,2.14894550),vec2(-5.12000000,2.40000000),vec2(-5.08694810,2.65105450),vec2(-4.99004460,2.88500000),vec2(-4.83589360,3.08589360),vec2(-4.63500000,3.24004460),vec2(-4.40105450,3.33694810),vec2(-4.15000000,3.37000000));
const vec3 wheels[5]=vec3[](vec3(-4.15000000,-0.60000000,0.88000000),vec3(-2.55000000,-1.85000000,0.80000000),vec3(0.00000000,-1.82000000,0.83000000),vec3(2.55000000,-1.85000000,0.80000000),vec3(4.15000000,-0.60000000,0.88000000));
vec4 belt(float phase){
    float total=0.;for(int i=0;i<28;i++){total+=length(path[i+1]-path[i]);}
    float s=mod(phase,total);
    for(int i=0;i<28;i++){
        vec2 d=path[i+1]-path[i];float len=length(d);
        if(s<=len){return vec4(path[i]+d*s/len-vec2(0.,3.00000000),d/len);}s-=len;
    }
    return vec4(path[0]-vec2(0.,3.00000000),1.,0.);
}






vec4 live_belt(float phase,int row,float total){
    float s=mod(phase/23.43539363436418*total,total);
    for(int i=0;i<16;i++){
        vec4 a=texelFetch(track_state,ivec2(4+i,row),0);vec4 b=texelFetch(track_state,ivec2(20+i,row),0);
        if(b.x<=0.){continue;}
        if(s<=b.x){
            if(b.z>.5){float angle=a.w+b.y*s/b.x;return vec4(a.xy+a.z*vec2(cos(angle),sin(angle))-vec2(0.,3.),vec2(sin(angle),-cos(angle)));}
            vec2 direction=normalize(a.zw-a.xy);return vec4(a.xy+direction*s-vec2(0.,3.),direction);
        }s-=b.x;
    }
    return vec4(0.,0.,1.,0.);
}


uniform float shade_softness = 0.05;
uniform float hatch_strength = 0.075;
varying vec3 surface_position;
varying vec3 surface_normal;
varying vec3 world_normal;
void vertex(){
    int row=state_row+(VERTEX.y>0.?0:1);
    vec4 suspension=texelFetch(track_state,ivec2(0,row),0);
    vec2 phase_length=texelFetch(track_state,ivec2(1,row),0).xy;
    vec4 angles=texelFetch(track_state,ivec2(2,row),0);
    float end_angle=texelFetch(track_state,ivec2(3,row),0).x;
    float travel_m=phase_length.x;vec3 offsets=suspension.xyz;
    // The glTF exporter flips V: static=1, belt=0, rolling wheel=-1.
    if(UV.y<-1.5){
        int index=clamp(int(round(UV.x)),1,4);
        if(index==4){VERTEX.x+=suspension.w;}else{VERTEX.z+=offsets[index-1];}
    }else if(UV.y<-.5){
        int index=clamp(int(round(UV.x)),0,4);
        vec3 wheel=wheels[index];float a=index==4?end_angle:angles[index];float c=cos(a);float s=sin(a);
        vec2 d=VERTEX.xz-wheel.xy;
        VERTEX.xz=wheel.xy+vec2(c*d.x-s*d.y,s*d.x+c*d.y);
        if(index>0 && index<4){VERTEX.z+=offsets[index-1];}
        if(index==4){VERTEX.x+=suspension.w;}
        vec2 n=NORMAL.xz;NORMAL.xz=vec2(c*n.x-s*n.y,s*n.x+c*n.y);
    }else if(UV.y<.5){
        vec4 old=belt(UV.x);vec4 next=live_belt(UV.x+travel_m,row,phase_length.y);
        vec2 oldn=vec2(-old.w,old.z);vec2 newn=vec2(-next.w,next.z);
        vec2 delta=VERTEX.xz-old.xy;
        VERTEX.xz=next.xy+next.zw*dot(delta,old.zw)+newn*dot(delta,oldn);
        NORMAL.xz=next.zw*dot(NORMAL.xz,old.zw)+newn*dot(NORMAL.xz,oldn);
    }
surface_position=VERTEX;surface_normal=NORMAL;world_normal=MODEL_NORMAL_MATRIX*NORMAL;
}
void fragment() {
    vec3 an = abs(surface_normal);
    vec2 p = surface_position.xy;
    if (an.y > an.x && an.y > an.z) { p = surface_position.xz; }
    else if (an.x > an.z) { p = surface_position.zy; }
    float coordinate = (p.x + p.y * 0.62) * 330.0;
    float footprint = fwidth(coordinate);
    float distance_to_line = abs(fract(coordinate) - 0.5);
    float line = 1.0 - smoothstep(0.045, 0.045 + footprint, distance_to_line);
    float fade = 1.0 - smoothstep(0.16, 0.50, footprint);
    float shade = 1.0 - smoothstep(0.10,0.65,dot(normalize(world_normal), normalize(vec3(-0.4,0.8,0.3))));
    ALBEDO = paint.rgb * (1.0 - line * fade * shade * hatch_strength);
    ROUGHNESS = 0.95;
}
void light() {
    float n = dot(NORMAL, LIGHT);
    float middle = smoothstep(0.08 - shade_softness, 0.08 + shade_softness, n);
    float bright = smoothstep(0.60 - shade_softness, 0.60 + shade_softness, n);
    float band = 0.12 + middle * 0.48 + bright * 0.26;
    DIFFUSE_LIGHT += LIGHT_COLOR * band * ATTENUATION / 3.14159265;
}
