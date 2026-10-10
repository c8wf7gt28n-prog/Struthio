# R13 symmetric controls — assembly prototypes

Visible centerline: X=+1.20 mm, matching the fixed panel body center.
Primary button face centers: X=-39.55 and +41.95 mm, Y=102 mm.
Visible screen-facing flats: X=-34.35 and +36.75 mm. Each visible panel-to-button separation is 2.50 mm: 0.20 mm panel clearance + 2.00 mm solid bezel + 0.30 mm button clearance. Lower retaining flanges retain the previous narrower cuts to preserve the stop legs. Bezel reference rails occupy Z=5.65..7.65 mm and are provided as STEP references, not separate parts for printing. Integrate them continuously into the future shell above and below the buttons; final retention and travel remain unverified.
DART visible face center: X=+1.20 mm. Upper material above Z=5.65 is translated +1.20 mm; all lower mechanism geometry retains the original coordinates except cap edge clearance cuts.

The contact nubs, stop legs and DART pivot stay at their original R26/R12 mechanism coordinates. Visible caps and rocker are reflection-symmetric around the screen-body centerline. Hidden lower mechanisms are intentionally not mirrored about that line because switch and pivot locations remain fixed.

Checks: valid single B-rep solids; closed STL edges; no degenerate STL triangles; zero nominal intersection with the conditional panel envelope; upper cap mirror and rocker mirror differences below 0.00001 mm³.

NOT A PRINT-READY CASE RELEASE. Existing R12 shell holes do not accommodate the shifted controls. Matching keyed guides, retention, travel stops and updated shell outline are still required. No moving assembly, tolerance-stack, fatigue or acoustic verification is claimed. Rocker force balance needs checking because the visible face is offset from its pivot. The upper/lower join is a boolean union, without a newly optimized fillet. Panel Z=5.00..6.85 mm remains an assumed old-case datum. Active-area center within the panel is not yet confirmed. Exterior shell and acoustic chambers are NOT changed in this package.

STL units are mm. STEP and editable generator included. Generator expects the source R31 case STEP files under case_update/input.
