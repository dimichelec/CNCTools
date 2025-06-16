import math
import argparse
import sys

Version = "0.3.2"

"""
This script generates a CNC test pattern in G-code to used in testing V bit carving of copper cladded board
generally used in creating PCBs.

It creates a grid of squares testing two factors, for example, Z cutting depth on the grid X axis, and XY speed
on the grid Y axis.

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
    --x_mode          Parameter to sweep over X axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle, 4 - fill_step (default: 1)
    --x_steps         Grid steps on the X axis (default: 3)
    --y_mode          Parameter to sweep over Y axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle, 4 - fill_step (default: 2)
    --y_steps         Grid steps on the Y axis (default: 3)
    --z_pass          Passing Z height for rapid moves (default: 0.050in)
    --z_speed         Z-axis cutting speed (default: 2.0ipm)
    --square_size     Square side length (default: 0.050in)
    --fill_square     Fill square: 0 - no, 1 - yes (default: 0)
    --fill_step_start Step size when filling square start (default: 0.004in)
    --fill_step_step  Step size when filling square step (default: 0.000in)
    --gap_size        Gap size between squares (default: 0.050in)
    --x_idle          Idle/safe X height (default: 0.000in)
    --y_idle          Idle/safe Y height (default: 0.000in)
    --z_idle          Idle/safe Z height (default: 0.500in)
    --quadrant        Quadrant of grid: 1 = +X/+Y, 2 = -X/+Y, 3 = -X/-Y, 4 = +X/-Y (default: 2)
    --x_start         Starting X coordinate for the pattern (default: -0.150in)
    --y_start         Starting Y coordinate for the pattern (default: 0.000in)

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
parser.add_argument("--x_mode", type=int, default=1, help="Parameter to sweep over X axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle, 4 - fill_step (default: 1)")
parser.add_argument("--x_steps", type=int, default=3, help="Grid steps on the X axis (default: 3)")
parser.add_argument("--y_mode", type=int, default=2, help="Parameter to sweep over Y axis: 0 - none, 1 - z_cut, 2 - xy_speed, 3 - spindle, 4 - fill_step (default: 2)")
parser.add_argument("--y_steps", type=int, default=3, help="Grid steps on the Y axis (default: 3)")
parser.add_argument("--z_pass", type=float, default=0.050, help="Passing Z height (default: 0.050in)")
parser.add_argument("--z_speed", type=float, default=2.0, help="Z cutting speed (default: 2.0ipm)")
parser.add_argument("--square_size", type=float, default=0.050, help="Square side length (default: 0.050in)")
parser.add_argument("--fill_square", type=int, default=0, help="Fill square: 0 - no, 1 - yes (default: 0)")
parser.add_argument("--fill_step_start", type=float, default=0.004, help="Step size when filling square start (default: 0.004in)")
parser.add_argument("--fill_step_step", type=float, default=0.000, help="Step size when filling square step (default: 0.000in)")
parser.add_argument("--gap_size", type=float, default=0.050, help="Gap size between squares (default: 0.050in)")
parser.add_argument("--x_idle", type=float, default=0.000, help="Idle/safe X coordinate (default: 0.000in)")
parser.add_argument("--y_idle", type=float, default=0.000, help="Idle/safe Y coordinate (default: 0.000in)")
parser.add_argument("--z_idle", type=float, default=0.500, help="Idle/safe Z height (default: 0.500in)")
parser.add_argument("--quadrant", type=int, default=2, help="Quadrant of grid: 1 = +X/+Y, 2 = -X/+Y, 3 = -X/-Y, 4 = +X/-Y (default: 2)")
parser.add_argument("--x_start", type=float, default=-0.150, help="Starting X coordinate for the pattern (default: -0.150in)")
parser.add_argument("--y_start", type=float, default=0.0, help="Starting Y coordinate for the pattern (default: 0.000in)")

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
        self.square_size = args.square_size
        self.fill_square = args.fill_square
        self.fill_step_start = args.fill_step_start
        self.fill_step_step = args.fill_step_step
        self.gap_size = args.gap_size
        self.x_idle = args.x_idle
        self.y_idle = args.y_idle
        self.z_idle = args.z_idle
        self.quadrant = args.quadrant
        self.x_start = args.x_start
        self.y_start = args.y_start

        # TODO: units = args.units

config = Config()

class Gcode:
    def __init__(self):
        self.units = "in"           # "in" or "mm"
        self.coord_fmt = ".5f"      # coordinate format
        self.speed_fmt = ".4f"      # speed format
        self.rpm_fmt = "d"          # spindle speed format
        self.comment_pos = 8        # position of comments

gcode = Gcode()

# Writes a single line of G-code (with optional comment) to the specified file.
def write_gcode_line(file, command="", comment=None):
    """ Writes a single line of G-code to the specified file. """
    line = command
    if comment:
        line = f"{line:<{gcode.comment_pos}}; {comment}"
    file.write(line + "\n")

# Writes G-code to 'outfile' for a grid of squares with optional filling, using provided sweep descriptions and square parameters.
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
        write_gcode_line(file, "; Args:")
        [write_gcode_line(file, f"; {line}") for line in cmdline_str]
        write_gcode_line(file)

        write_gcode_line(file, f"G0 Z{config.z_idle: = {gcode.coord_fmt}}")
        write_gcode_line(file, f"M3 S{config.spindle_start:{gcode.rpm_fmt}}")
        write_gcode_line(file, "G4 P2", "2sec pause")   # Pause for the spindle to get to speed
        write_gcode_line(file)

        last_spindle = config.spindle_start
        first_square = True
        for square in squares:
            x, y, z_cut, xy_speed, spindle, fill_step = square

            # If we're changing spindle speed, pause for 2sec before cutting
            if (spindle != last_spindle):
                write_gcode_line(file, f"M3 S{spindle:{gcode.rpm_fmt}}")
                write_gcode_line(file, "G4 P2", "2sec pause")
                last_spindle = spindle

            write_gcode_line(file, f"G0 X{x: = {gcode.coord_fmt}} Y{y: = {gcode.coord_fmt}}")
            if first_square:
                write_gcode_line(file, f"G0 Z{config.z_pass: = {gcode.coord_fmt}}")
                first_square = False

            write_gcode_line(file, f"G1 Z{z_cut: = {gcode.coord_fmt}} F{config.z_speed:{gcode.speed_fmt}}")

            if config.fill_square:
                # Ensure at least one pass
                num_passes = max(1, int(math.ceil(config.square_size / fill_step)))
                for i in range(num_passes):
                    y0 = y + i * fill_step
                    y1 = min(y + config.square_size, y0 + fill_step)
                    if i % 2 == 0:
                        # Left to right
                        write_gcode_line(file, f"G1 X{x: = {gcode.coord_fmt}} Y{y0: = {gcode.coord_fmt}} F{xy_speed:{gcode.speed_fmt}}")
                        write_gcode_line(file, f"   X{x + config.square_size: = {gcode.coord_fmt}} Y{y0: = {gcode.coord_fmt}}")
                    else:
                        # Right to left
                        write_gcode_line(file, f"G1 X{x + config.square_size: = {gcode.coord_fmt}} Y{y0: = {gcode.coord_fmt}} F{xy_speed:{gcode.speed_fmt}}")
                        write_gcode_line(file, f"   X{x: = {gcode.coord_fmt}} Y{y0: = {gcode.coord_fmt}}")
            else:
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
    
    param_name = {1: "z_cut",            2: "xy_speed",            3: "spindle",            4: "fill_step"            }[mode]
    fmt =        {1: gcode.coord_fmt,    2: gcode.speed_fmt,       3: gcode.rpm_fmt,        4: gcode.coord_fmt        }[mode]
    start =      {1: config.z_cut_start, 2: config.xy_speed_start, 3: config.spindle_start, 4: config.fill_step_start }[mode]
    step =       {1: config.z_cut_step,  2: config.xy_speed_step,  3: config.spindle_step,  4: config.fill_step_step  }[mode]

    values = ", ".join([f"{start + i * step:{fmt}}" for i in range(steps)])
    return f"{f'Sweeping {param_name} over {axis} axis:':<30} [{values}]"

# Generate an array of strings reporting the command-line arguments used
def build_cmdline_str(argv, outfile):
    """
    Build a list of strings representing the command-line call, each <= 80 chars,
    not splitting arguments. Exclude outfile argument.
    """
    cmdline_str = []
    current = ""
    for arg in argv:
        if arg == outfile:
            continue
        if current and len(current) + 1 + len(arg) > 80:
            cmdline_str.append(current)
            current = arg
        else:
            if current:
                current += " " + arg
            else:
                current = arg
    if current:
        cmdline_str.append(current)
    return cmdline_str

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

    # Create a printable string of the command-line call that ran this program
    cmdline_str = build_cmdline_str(sys.argv[1:], args.outfile)

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
    fill_step = config.fill_step_start

    # Initialize the starting Y coordinate for the grid
    y = config.y_start
    # If we're cutting in a -Y quadrant, start Y at the far end of the grid
    if config.quadrant == 3 or config.quadrant == 4:
        y = y - (config.y_steps * config.square_size) - ((config.y_steps - 1) * config.gap_size)

    for y_step in range(config.y_steps):
        x = config.x_start
        # If we're cutting in a -X quadrant, start X at the far end of the grid
        if config.quadrant == 2 or config.quadrant == 3:
            x = x - (config.x_steps * config.square_size) - ((config.x_steps - 1) * config.gap_size)

        # Reset the parameter being swept over the X axis based on x_mode
        if config.x_mode == 1:      # Sweep over z_cut
            z_cut = config.z_cut_start
        elif config.x_mode == 2:    # Sweep over xy_speed
            xy_speed = config.xy_speed_start
        elif config.x_mode == 3:    # Sweep over spindle speed
            spindle = config.spindle_start
        elif config.x_mode == 4:    # Sweep over fill_step
            fill_step = config.fill_step_start

        # Iterate through each square in the current row
        for x_step in range(config.x_steps):
            # Add the square's parameters to the list
            squares.append((x, y, z_cut, xy_speed, spindle, fill_step))
            # Move to the next square in the row
            x = x + config.square_size + config.gap_size

            # Increment the parameter being swept over the X axis
            if config.x_mode == 1:      # Sweep over z_cut
                z_cut = z_cut + config.z_cut_step
            elif config.x_mode == 2:    # Sweep over xy_speed
                xy_speed = xy_speed + config.xy_speed_step
            elif config.x_mode == 3:    # Sweep over spindle speed
                spindle = spindle + config.spindle_step
            elif config.x_mode == 4:    # Sweep over fill_step
                fill_step = fill_step + config.fill_step_step

        # Move to the next row in the grid
        y = y + config.square_size + config.gap_size

        # Increment the parameter being swept over the Y axis
        if config.y_mode == 1:      # Sweep over z_cut
            z_cut = z_cut + config.z_cut_step
        elif config.y_mode == 2:    # Sweep over xy_speed
            xy_speed = xy_speed + config.xy_speed_step
        elif config.y_mode == 3:    # Sweep over spindle speed
            spindle = spindle + config.spindle_step
        elif config.y_mode == 4:    # Sweep over fill_step
            fill_step = fill_step + config.fill_step_step

    write_squares(args.outfile, x_sweep_str, y_sweep_str, squares)

    print(f"G-code saved as '{args.outfile}'")
    
