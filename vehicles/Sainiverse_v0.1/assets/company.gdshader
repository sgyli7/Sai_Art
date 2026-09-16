shader_type spatial;
render_mode cull_back;
uniform sampler2D company_atlas:source_color,filter_linear_mipmap_anisotropic,repeat_disable;
void fragment(){
 vec4 label=texture(company_atlas,UV);
 if(label.a<.5){discard;}
 ALBEDO=label.rgb;ROUGHNESS=.86;
}
void light(){
 float n=dot(NORMAL,LIGHT);float band=.18+smoothstep(.04,.16,n)*.44+smoothstep(.52,.68,n)*.25;
 DIFFUSE_LIGHT+=LIGHT_COLOR*(band*.8+max(n,0.)*.2)*ATTENUATION/3.14159265;
}
