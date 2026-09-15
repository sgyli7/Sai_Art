shader_type spatial;
uniform vec4 pigment:source_color=vec4(.3,.3,.3,1.);
uniform sampler2D detail_normal:hint_normal,filter_linear_mipmap_anisotropic,repeat_enable;
uniform float normal_strength=.80;
uniform sampler2D artwork:filter_linear_mipmap_anisotropic,repeat_disable;
uniform sampler2D wear_map:filter_linear_mipmap_anisotropic,repeat_disable;
uniform sampler2D wordmark:source_color,filter_linear_mipmap_anisotropic,repeat_disable;
uniform sampler2D warning_map:source_color,filter_linear_mipmap_anisotropic,repeat_disable;
uniform vec4 body_pigment:source_color=vec4(.12,.12,.12,1.);
uniform float artwork_strength=.70;
uniform sampler2D surface_atlas:filter_linear_mipmap_anisotropic,repeat_disable;
uniform sampler2D surface_normal:hint_normal,filter_linear_mipmap_anisotropic,repeat_disable;
uniform float indicator_on=-1.;
uniform sampler2D equipment_labels:source_color,filter_linear_mipmap_anisotropic,repeat_disable;
uniform int label_id=0;
uniform float tile_m=4.;
uniform int surface_kind=0;
uniform float hatch_strength=0.;
varying vec3 source_p;
varying vec3 source_n;
varying vec3 ground_p;
float line(float x,float w){return 1.-smoothstep(w,w+max(fwidth(x),.0001),abs(x));}
void vertex(){source_p=VERTEX;source_n=NORMAL;ground_p=(MODEL_MATRIX*vec4(VERTEX,1.)).xyz;}
void fragment(){
 vec3 an=abs(source_n);vec2 p=source_p.xy;
 if(an.y>an.x && an.y>an.z){p=source_p.xz;}else if(an.x>an.z){p=source_p.zy;}
 bool deck_side=surface_kind==1 && abs(source_n.z)<.65;
 ALBEDO=deck_side?body_pigment.rgb:pigment.rgb;ROUGHNESS=surface_kind==1?.70:.88;
 if(surface_kind!=3 && UV2.x>=0.){
  float index=floor(UV2.x);vec2 cell=vec2(mod(index,4.),floor(index/4.));
  vec2 local_uv=vec2(fract(UV2.x),UV2.y);
  if(index>=6. && index<8.){local_uv=fract(vec2((fract(UV2.x)-.00001)*4096.,UV2.y)/vec2(8.,4.));local_uv=.016+local_uv*.968;}
  vec2 uv2=(cell+local_uv)*.25;
  float coating=texture(surface_atlas,uv2).r;
  ALBEDO*=clamp(coating/.56,.45,1.40);
  vec3 detail=texture(surface_normal,uv2).xyz*2.-1.;
  vec3 dp1=dFdx(VERTEX),dp2=dFdy(VERTEX);vec2 du1=dFdx(uv2),du2=dFdy(uv2);
  vec3 t=cross(dp2,NORMAL)*du1.x+cross(NORMAL,dp1)*du2.x;
  vec3 b=cross(dp2,NORMAL)*du1.y+cross(NORMAL,dp1)*du2.y;
  float nscale=inversesqrt(max(max(dot(t,t),dot(b,b)),.000001));
  NORMAL=normalize(mat3(t*nscale,b*nscale,NORMAL)*vec3(detail.xy*.65,detail.z));
 }
 if(surface_kind!=3){
  bool mapped_wear=surface_kind==0 && UV.x>=0. && UV.x<=1.;
  vec2 uv=(surface_kind>=4 || mapped_wear)?vec2(UV.x,1.-UV.y):p/tile_m;
  bool painted=surface_kind==4;vec2 cover_uv=vec2(0.);float cover_cell=0.;bool cover=false;
  if(surface_kind==5 && source_n.y<-.5){
   float u=clamp((source_p.x+7.4)/3.8,0.,2.9999);float cell=floor(u);
   vec2 local_uv=vec2(fract(u),1.-clamp((source_p.z-.9)/6.,0.,1.));
   cover_uv=local_uv;cover_cell=cell;cover=true;
   uv=(clamp(local_uv,vec2(.002),vec2(.998))+vec2(mod(cell,2.),floor(cell/2.)))*.5;painted=true;
  }
  if(painted){vec4 tex=texture(artwork,uv);float a=mix(.55,tex.r,tex.a);ALBEDO*=mix(1.,clamp(a/.55,.15,1.7),artwork_strength);}

  if(surface_kind==8 || mapped_wear || cover){
   vec2 mask_uv=cover?(clamp(cover_uv,vec2(.002),vec2(.998))+vec2(cover_cell,0.))/4.:uv;
   vec3 wear=texture(wear_map,mask_uv).rgb;
   ALBEDO=mix(ALBEDO,vec3(.065,.070,.071),wear.r*.70);ALBEDO*=1.-wear.g*.4;ALBEDO+=wear.b*.012;
  }
  if(cover){
   vec2 label=cover_cell<.5?(cover_uv-vec2(.22,.53))/vec2(.35,.23):(cover_uv-vec2(.13,.59))/vec2(.74,.065);
   if(all(greaterThanEqual(label,vec2(0.))) && all(lessThanEqual(label,vec2(1.)))){
    vec4 ink=texture(wordmark,vec2(label.x,(label.y+cover_cell)/4.));vec3 ink_color=dot(body_pigment.rgb,vec3(.2126,.7152,.0722))>.25?vec3(.028,.032,.035):ink.rgb;ALBEDO=mix(ALBEDO,ink_color,ink.a*.80);
   }
  }
  if(surface_kind==10 && all(greaterThanEqual(uv,vec2(0.))) && all(lessThanEqual(uv,vec2(1.)))){
   vec4 label=texture(equipment_labels,(uv+vec2(float(label_id%4),float(label_id/4)))*.25);ALBEDO=mix(ALBEDO,label.rgb,label.a);
  }
  if(surface_kind==7){
   if(dot(body_pigment.rgb,vec3(.2126,.7152,.0722))>.25){ALBEDO=vec3(.028,.032,.035);}
   float loss=texture(wear_map,uv).r;ALBEDO=mix(ALBEDO,body_pigment.rgb,clamp(loss*1.35,0.,1.));
  }
  if(surface_kind==6){
   vec2 q=fract(uv*4.);float variant=mod(floor(uv.x*4.),4.);
   // Paint the existing physical edge plate; no floating decal geometry.
   vec2 strip=vec2(q.y*(an.x>.8?.125:1.),(q.x+variant)/4.);ALBEDO=texture(warning_map,strip).rgb;
  }
  if(surface_kind==1 && !deck_side){
  vec3 detail=texture(detail_normal,uv).xyz*2.-1.;
  // Derivative cotangent frame aligns the data map to each source-space plane,
  // including vertical panels and moving source groups without authored UVs.
  vec3 dp1=dFdx(VERTEX),dp2=dFdy(VERTEX);vec2 duv1=dFdx(uv),duv2=dFdy(uv);
  vec3 dp2perp=cross(dp2,NORMAL),dp1perp=cross(NORMAL,dp1);
  vec3 t=dp2perp*duv1.x+dp1perp*duv2.x;vec3 b=dp2perp*duv1.y+dp1perp*duv2.y;
  float scale=inversesqrt(max(max(dot(t,t),dot(b,b)),.000001));
  NORMAL=normalize(mat3(t*scale,b*scale,NORMAL)*vec3(detail.xy*normal_strength,detail.z));
  }
 }
 if(indicator_on>=0.){ALBEDO=pigment.rgb*mix(.20,1.,indicator_on);EMISSION=pigment.rgb*indicator_on*.45;}
 if(surface_kind==3){
  vec2 q=ground_p.xz;float height_tone=clamp(ground_p.y*.035,-.10,.20);
  ALBEDO=vec3(.32,.34,.29)+height_tone;
  float contours=line(fract(ground_p.y*1.+.5)-.5,.010)*(1.-smoothstep(.2,.7,fwidth(ground_p.y*1.)));
  vec2 cell=abs(fract(q/5.)-.5);float grid=max(line(cell.x-.5,.001),line(cell.y-.5,.001));
  grid*=1.-smoothstep(.02,.09,max(fwidth(q.x/5.),fwidth(q.y/5.)));
  ALBEDO*=1.-contours*.10;ALBEDO=mix(ALBEDO,vec3(.52,.51,.43),grid*.35);ROUGHNESS=1.;
 }
}
void light(){
 float n=dot(NORMAL,LIGHT);float band=surface_kind==3?max(n,0.):(.18+smoothstep(.04,.16,n)*.44+smoothstep(.52,.68,n)*.25);
 DIFFUSE_LIGHT+=LIGHT_COLOR*(band*.80+max(n,0.)*.20)*ATTENUATION/3.14159265;
 if(surface_kind!=3){float spec=pow(max(dot(NORMAL,normalize(VIEW+LIGHT)),0.),18.);SPECULAR_LIGHT+=LIGHT_COLOR*spec*.025*(1.-ROUGHNESS*.75)*ATTENUATION;}
}
