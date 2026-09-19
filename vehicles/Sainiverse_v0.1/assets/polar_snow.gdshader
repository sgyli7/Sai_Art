shader_type spatial;
render_mode cull_back;

varying vec3 world_normal;

void vertex() {
    world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}

void fragment() {
    float slope = 1.0 - clamp(world_normal.y, 0.0, 1.0);
    ALBEDO = mix(vec3(0.60, 0.67, 0.72), vec3(0.48, 0.57, 0.65), smoothstep(0.12, 0.55, slope));
    ROUGHNESS = 1.0;
}
