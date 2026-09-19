shader_type sky;

void sky() {
    float elevation = max(EYEDIR.y, 0.0);
    vec3 horizon = vec3(0.64, 0.74, 0.81);
    vec3 zenith = vec3(0.32, 0.49, 0.67);
    COLOR = mix(horizon, zenith, pow(elevation, 0.55));
}
