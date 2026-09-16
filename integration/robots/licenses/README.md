# Runtime snapshot provenance
This private review includes robot runtime files from the user's existing Sim2Sim checkout, plus the native learned-policy binaries needed to replay the four vehicle missions.

MicroDuck meshes are converted from Pollen Robotics microduck_rl (https://github.com/pollen-robotics/microduck_rl). Its README assigns 3D models Creative Commons BY-SA-NC; its software is Apache-2.0. Original model authors retain their rights; this private review does not relicense those meshes as vehicle code. Mesh conversion and presentation shaders are Sim2Sim integration changes. Policies are reused from the prepared local deployment; deployment.json preserves hashes and provenance.

Sai source/model: https://github.com/sgyli7/Sai_Agent_001, release alpha.3. Per-part notices retained in Sai/. Godot-cpp and ONNX Runtime are MIT, Noto CJK is SIL OFL. Existing Sim2Sim notices are preserved verbatim; their statement about excluded assets describes that upstream repository, while this local review snapshot additionally contains the above runtime assets.
