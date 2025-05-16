import math
import argparse

Version = 0.1

"""
This script generates a CNC test pattern in G-code to used in testing V bit carving of copper cladded board
generally used in creating PCBs.

It creates a grid of squares in quadrant II, to the left of the typical board area in quadrant I. The grid
of squares could test two factors, for example, Z cutting depth on the grid X axis, and XY speed on the
grid Y axis.

Usage:
    python test_pattern.py <outfile> [options]
Arguments:
    outfile     Path to the output G-code file.
Options:
    --z_cut_start     Starting depth for cutting operations (default: -0.000in)
    --z_cut_step      Depth increment for each cutting pass (default: -0.000in)
    --xy_speed_start  Initial XY cutting speed (default: 4.0ipm)
    --xy_speed_step   Increment in XY cutting speed for each pass (default: 0.0ipm)
    --spindle_start   Initial spindle speed (default: 10000rpm)
    --spindle_step    Increment in spindle speed for each pass (default: 0rpm)
    --x_mode          Parameter to sweep over X axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle (default: 1)
    --x_steps         Grid steps on the X axis (default: 3)
    --y_mode          Parameter to sweep over Y axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle (default: 2)
    --y_steps         Grid steps on the Y axis (default: 3)
    --z_pass          Passing Z height for rapid moves (default: 0.050in)
    --z_speed         Z-axis cutting speed (default: 2.0ipm)
    --x_start         Starting X coordinate for the pattern (default: -0.150in)
    --y_start         Starting Y coordinate for the pattern (default: 0.000in)
    --square_size     Square side length (default: 0.050in)
    --gap_size        Gap size between squares (default: 0.050in)
    --x_idle          Idle/safe X height (default: 0.000in)
    --y_idle          Idle/safe Y height (default: 0.000in)
    --z_idle          Idle/safe Z height (default: 0.500in)

Dependencies:
- Python 3.x
"""

parser = argparse.ArgumentParser(description=f"Create a CNC/PCB G-code test pattern (v{Version})")
parser.add_argument("outfile", help="Output G-code filename")
parser.add_argument("--z_cut_start", type=float, default=-0.000, help="Cutting Z start depth (default: -0.000in)")
parser.add_argument("--z_cut_step", type=float, default=-0.000, help="Cutting Z depth step (default: -0.000in)")
parser.add_argument("--xy_speed_start", type=float, default=4.0, help="XY cutting speed start (default: 4.0ipm)")
parser.add_argument("--xy_speed_step", type=float, default=0.0, help="XY cutting speed step (default: 0.0ipm)")
parser.add_argument("--spindle_start", type=int, default=10000, help="Spindle speed start (default: 10000rpm)")
parser.add_argument("--spindle_step", type=int, default=0, help="Spindle speed step (default: 0rpm)")
parser.add_argument("--x_mode", type=int, default=1, help="Parameter to sweep over X axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle (default: 1)")
parser.add_argument("--x_steps", type=int, default=3, help="Grid steps on the X axis (default: 3)")
parser.add_argument("--y_mode", type=int, default=2, help="Parameter to sweep over Y axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle (default: 2)")
parser.add_argument("--y_steps", type=int, default=3, help="Grid steps on the Y axis (default: 3)")
parser.add_argument("--z_pass", type=float, default=0.050, help="Passing Z height (default: 0.050in)")
parser.add_argument("--z_speed", type=float, default=2.0, help="Z cutting speed (default: 2.0ipm)")
parser.add_argument("--x_start", type=float, default=-0.150, help="Starting X coordinate for the pattern (default: -0.150in)")
parser.add_argument("--y_start", type=float, default=0.0, help="Starting Y coordinate for the pattern (default: 0.000in)")
parser.add_argument("--square_size", type=float, default=0.050, help="Square side length (default: 0.050in)")
parser.add_argument("--gap_size", type=float, default=0.050, help="Gap size between squares (default: 0.050in)")
parser.add_argument("--x_idle", type=float, default=0.000, help="Idle/safe X coordinate (default: 0.000in)")
parser.add_argument("--y_idle", type=float, default=0.000, help="Idle/safe Y coordinate (default: 0.000in)")
parser.add_argument("--z_idle", type=float, default=0.500, help="Idle/safe Z height (default: 0.500in)")

args = parser.parse_args()


class Config:
    def __init__(self):
        self.z_cut_start = args.z_cut_start
        self.z_cut_step = args.z_cut_step
        self.xy_speed_start = args.xy_speed_start
        self.xy_speed_step = args.xy_speed_step
        self.spindle_start = args.spindle_start
        self.spindle_step = args.spindle_step
        self.x_mode = args.x_mode
        self.x_steps = args.x_steps
        self.y_mode = args.y_mode
        self.y_steps = args.y_steps
        self.z_pass = args.z_pass
        self.z_speed = args.z_speed
        self.x_start = args.x_start
        self.y_start = args.y_start
        self.square_size = args.square_size
        self.gap_size = args.gap_size
        self.x_idle = args.x_idle
        self.y_idle = args.y_idle
        self.z_idle = args.z_idle
        # TODO: units = args.units

config = Config()


class Gcode:
    def __init__(self):
        self.units = "in"           # "in" or "mm"
        self.coord_fmt = ".5f"      # coordinate format
        self.speed_fmt = ".4f"      # speed format
        self.rpm_fmt = "d"         # spindle speed format
        self.comment_pos = 8        # position of comments

gcode = Gcode()

def write_gcode_line(file, command="", comment=None):
    """ Writes a single line of G-code to the specified file. """
    line = command
    if comment:
        line = f"{line:<{gcode.comment_pos}}; {comment}"
    file.write(line + "\n")

def write_squares(outfile, x_sweep_str, y_sweep_str, squares):

    with open(outfile, 'w') as file:

        write_gcode_line(file)

        write_gcode_line(file, "G20", "inches")
        write_gcode_line(file, "G90", "absolute coordinates")
        write_gcode_line(file, "G94", "units per minute feedrates")
        write_gcode_line(file)

        write_gcode_line(file, f"; {x_sweep_str}")
        write_gcode_line(file, f"; {y_sweep_str}")
        write_gcode_line(file)

        write_gcode_line(file, f"G0 Z{config.z_idle: = {gcode.coord_fmt}}")
        write_gcode_line(file, f"M3 S{config.spindle_start:{gcode.rpm_fmt}}")
        write_gcode_line(file)

        for square in squares:
            x, y, z_cut, xy_speed, spindle = square
            if (config.spindle_step != 0):
                write_gcode_line(file, f"M3 S{spindle:{gcode.rpm_fmt}}")
                write_gcode_line(file, "G4 P2", "2sec pause")

            write_gcode_line(file, f"G0 X{x: = {gcode.coord_fmt}} Y{y: = {gcode.coord_fmt}}")
            write_gcode_line(file, f"G1 Z{z_cut: = {gcode.coord_fmt}} F{config.z_speed:{gcode.speed_fmt}}")
            write_gcode_line(file, f"G1 X{x + config.square_size: = {gcode.coord_fmt}} Y{y: = {gcode.coord_fmt}} F{xy_speed:{gcode.speed_fmt}}")
            write_gcode_line(file, f"   Y{y + config.square_size: = {gcode.coord_fmt}}")
            write_gcode_line(file, f"   X{x: = {gcode.coord_fmt}}")
            write_gcode_line(file, f"   Y{y: = {gcode.coord_fmt}}")
            write_gcode_line(file, f"G0 Z{config.z_pass: = {gcode.coord_fmt}}")
            write_gcode_line(file)

        write_gcode_line(file, f"G0 Z{config.z_idle: = {gcode.coord_fmt}}")
        write_gcode_line(file, f"G0 X{config.x_idle: = {gcode.coord_fmt}} Y{config.y_idle: = {gcode.coord_fmt}}")
        write_gcode_line(file, "M5")
        write_gcode_line(file)

# Helper function to generate sweep description strings
def generate_sweep_string(axis, mode, steps):
    if mode == 0:
        return f"No {axis} axis sweep"
    
    param_name = {1: "z_cut",            2: "xy_speed",            3: "spindle"           }[mode]
    fmt =        {1: gcode.coord_fmt,    2: gcode.speed_fmt,       3: gcode.rpm_fmt       }[mode]
    start =      {1: config.z_cut_start, 2: config.xy_speed_start, 3: config.spindle_start}[mode]
    step =       {1: config.z_cut_step,  2: config.xy_speed_step,  3: config.spindle_step }[mode]

    values = ", ".join([f"{start + i * step:{fmt}}" for i in range(steps)])
    return f"{f'Sweeping {param_name} over {axis} axis:':<30} [{values}]"


if __name__ == "__main__":
    """
    Create a CNC/PCB test pattern in G-code.

    This script generates a CNC test pattern in G-code to used in testing V bit carving of copper cladded board
    generally used in creating PCBs.

    It creates a grid of squares in quadrant II, to the left of the typical board area in quadrant I. The grid
    of squares could test two factors, for example, Z cutting depth on the grid X axis, and XY speed on the
    grid Y axis.
    """

    if len(vars(args)) == 0:
        parser.print_help()
        exit(1)

    # Generate X and Y sweep description strings
    x_sweep_str = generate_sweep_string("X", config.x_mode, config.x_steps)
    y_sweep_str = generate_sweep_string("Y", config.y_mode, config.y_steps)

    # Print the output pattern description to the console
    print(x_sweep_str)
    print(y_sweep_str)

    squares = []

    z_cut = config.z_cut_start
    xy_speed = config.xy_speed_start
    spindle = config.spindle_start

    # Initialize the starting Y coordinate for the grid
    y = config.y_start

    for y_step in range(config.y_steps):
        # Calculate the starting X coordinate for the current row
        x = config.x_start - (config.x_steps * config.square_size) - ((config.x_steps - 1) * config.gap_size)

        # Reset the parameter being swept over the X axis based on x_mode
        if config.x_mode == 1:      # Sweep over z_cut
            z_cut = config.z_cut_start
        elif config.x_mode == 2:    # Sweep over xy_speed
            xy_speed = config.xy_speed_start
        elif config.x_mode == 3:    # Sweep over spindle speed
            spindle = config.spindle_start

        # Iterate through each square in the current row
        for x_step in range(config.x_steps):
            # Add the square's parameters to the list
            squares.append((x, y, z_cut, xy_speed, spindle))
            # Move to the next square in the row
            x = x + config.square_size + config.gap_size

            # Increment the parameter being swept over the X axis
            if config.x_mode == 1:      # Sweep over z_cut
                z_cut = z_cut + config.z_cut_step
            elif config.x_mode == 2:    # Sweep over xy_speed
                xy_speed = xy_speed + config.xy_speed_step
            elif config.x_mode == 3:    # Sweep over spindle speed
                spindle = spindle + config.spindle_step

        # Move to the next row in the grid
        y = y + config.square_size + config.gap_size

        # Increment the parameter being swept over the Y axis
        if config.y_mode == 1:      # Sweep over z_cut
            z_cut = z_cut + config.z_cut_step
        elif config.y_mode == 2:    # Sweep over xy_speed
            xy_speed = xy_speed + config.xy_speed_step
        elif config.y_mode == 3:    # Sweep over spindle speed
            spindle = spindle + config.spindle_step

    write_squares(args.outfile, x_sweep_str, y_sweep_str, squares)

    print(f"G-code saved as '{args.outfile}'")
    