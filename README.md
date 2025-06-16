# CNCTools

## svg_cutout.py v0.3
This script converts SVG paths into G-code filled rectangles for CNC machining.
I originally wrote this to remove solder mask from the pads on a PCB using CNC machining.

The script processes an input SVG file to extract rectangular paths, sorts them to minimize travel distance, 
and generates G-code commands to create spiraling or raster sweep paths that cover the rectangular areas.
The resulting G-code is saved to an output file.
### Usage
    python svg_cutout.py <infile> <outfile> [options]
### Arguments
    infile          Path to the input SVG file containing rectangular paths.
    outfile         Path to the output G-code file.
### Options
    --idle_z        Safe Z height for non-cutting moves (default: 0.500in)
    --pass_z        Passing Z height for rapid moves (default: 0.050in)
    --cut_z         Cutting Z height for material removal (default: 0.000in)
    --spindle       Spindle speed in RPM (default: 10000)
    --tool_dia      Tool diameter in inches (default: 0.015in)
    --overlap       Tool overlap between passes as a fraction (default: 0.15)
    --xy_speed      XY cutting speed in inches per minute (default: 4.0ipm)
    --z_speed       Z cutting speed in inches per minute (default: 2.0ipm)
    --shape         Shape of cutout: 1=spiral-in, 2=raster (default: 1)
    --raster_mode   Raster sweep mode: 0=auto, 1=vertical, 2=horizontal (default: 0)

## test_pattern.py v0.4
This script generates a CNC test pattern in G-code to used in testing V bit carving of copper cladded board
generally used in creating PCBs.

It creates a grid of squares testing two factors, for example, Z cutting depth on the grid X axis, and XY speed
on the grid Y axis.
### Usage
    python test_pattern.py <outfile> [options]
### Arguments
    outfile             Path to the output G-code file.
### Options
    --z_cut_start       Starting depth for cutting operations (default: 0.000in)
    --z_cut_step        Depth increment for each cutting pass (default: 0.000in)
    --xy_speed_start    Initial XY cutting speed (default: 4.0ipm)
    --xy_speed_step     Increment in XY cutting speed for each pass (default: 0.0ipm)
    --spindle_start     Initial spindle speed (default: 10000rpm)
    --spindle_step      Increment in spindle speed for each pass (default: 0rpm)
    --x_mode            Parameter to sweep over X axis: 0=none, 1=z_cut, 2=xy_speed, 3=spindle, 4=fill_step (default: 1)
    --x_steps           Grid steps on the X axis (default: 3)
    --y_mode            Parameter to sweep over Y axis: 0=none, 1=z_cut, 2=xy_speed, 3=spindle, 4=fill_step (default: 2)
    --y_steps           Grid steps on the Y axis (default: 3)
    --z_pass            Passing Z height for rapid moves (default: 0.050in)
    --z_speed           Z-axis cutting speed (default: 2.0ipm)
    --square_size       Square side length (default: 0.050in)
    --fill_square       Fill square: 0=no, 1=yes (default: 0)
    --fill_step_start   Step size when filling square start (default: 0.004in)
    --fill_step_step    Step size when filling square step (default: 0.000in)
    --gap_size          Gap size between squares (default: 0.050in)
    --x_idle            Idle/safe X height (default: 0.000in)
    --y_idle            Idle/safe Y height (default: 0.000in)
    --z_idle            Idle/safe Z height (default: 0.500in)
    --quadrant          Quadrant of grid: 1=+X/+Y, 2=-X/+Y, 3=-X/-Y, 4=+X/-Y (default: 2)
    --x_start           Starting X coordinate for the pattern (default: -0.150in)
    --y_start           Starting Y coordinate for the pattern (default: 0.000in)

