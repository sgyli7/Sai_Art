# Sai company identity / r032

The three source boards were provided directly by the user on 2026-09-17 for this Sainiverse project. Unmodified source PNGs and SHA-256 hashes are preserved in `assets/company/source/` and `assets/company/manifest.json`. These files are company artwork supplied for this project, not assets copied from MSFS or a third-party corporate identity.

`source/company_stickers.py` reproducibly extracts 6 clean light/dark marks and 17 weathered die cuts. The clean sheet has a baked checkerboard: background separation removes it. The weathered boards use explicitly traced, antialiased silhouettes, retaining the original interior printing, wear and lettering. Captions and demonstration photographs are excluded. Each individual PNG has alpha; the shared 2048 × 4096 atlas has padded, aspect-preserving placements.

`assets/company/contact_sheet.png` is an inspection sheet; `placements.json` records all installed locations, physical body ownership, sizes and face normals. The cockpit and lounge use small maker marks, ID plates and console strips; exterior cabin sides, deck fascias and crane pedestal hatches use larger weathered variants. Original overlapping manufacturer wordmark geometry was removed. Functional warning labels and instrument legends remain separate.

Decals are two triangles each on selected flat faces, with 3–17 mm stand-off depending on the underlying shell / trim geometry. Alpha discard prevents rectangular backing and avoids transparent sorting issues. All variants remain available for future use; placement is curated rather than randomly covering every surface.

## Interior finish

Existing inward cockpit-shell triangles are assigned to an independent lining material. There is no second coincident shell. Wall / ceiling / enclosure / worktop textures have distinct semantics. Bulkhead panels use 1.2 × 2.4 m scale; ceiling panels use 2.08 × 2.95 m scale. Surface colour and normal follow the same local metric projection; seat weave remains subtle and separate from panel pressings. Body-local coordinates also remain attached while the vehicle moves.

Do not pack metre coordinates into tiny fractional UV offsets beside atlas tile integers: the native imported result visibly distorted panel seams at that precision. Stable tile IDs select the texture family; metric coordinates come from local vertex positions. Blender uses the same projection.

These are stylized material and marking improvements. They do not establish parity with a commercial flight-simulator cockpit or validate real vehicle fabrication.
