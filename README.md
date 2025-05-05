# CNCTools

## svg_cutout.py
This script converts SVG paths into G-code spirals for CNC machining.
I originally wrote this to remove solder mask from the pads on a PCB using CNC machining.

The script processes an input SVG file to extract rectangular paths, sorts them to minimize travel distance, 
and generates G-code commands to create spiraling paths that cover the rectangular areas. The resulting G-code 
is saved to an output file.
### Usage
    python svg_cutout.py <infile> <outfile> [options]
### Arguments
    infile      Path to the input SVG file containing rectangular paths.
    outfile     Path to the output G-code file.
### Options
    --idle_z    Safe Z height for non-cutting moves (default: 1.000in).
    --pass_z    Passing Z height for rapid moves (default: 0.100in).
    --cut_z     Cutting Z height for material removal (default: -0.000in).
    --spindle   Spindle speed in RPM (default: 10000).
    --tool_dia  Tool diameter in inches (default: 0.015in).
    --overlap   Tool overlap between passes as a fraction (default: 0.15).
    --xy_speed  XY cutting speed in inches per minute (default: 4.0ipm).
    --z_speed   Z cutting speed in inches per minute (default: 0.40ipm).
