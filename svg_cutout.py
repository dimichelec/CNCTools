import math
from lxml import etree
import argparse
import sys


"""
This script converts SVG paths into G-code spirals for CNC machining.
I originally wrote this to remove solder mask from the pads on a PCB using CNC machining.

The script processes an input SVG file to extract rectangular paths, sorts them to minimize travel distance, 
and generates G-code commands to create spiraling paths that cover the rectangular areas. The resulting G-code 
is saved to an output file.

Usage:
    python svg_cutout.py <infile> <outfile> [options]
Arguments:
    infile      Path to the input SVG file containing rectangular paths.
    outfile     Path to the output G-code file.
Options:
    --idle_z    Safe Z height for non-cutting moves (default: 1.000in).
    --pass_z    Passing Z height for rapid moves (default: 0.100in).
    --cut_z     Cutting Z height for material removal (default: -0.000in).
    --spindle   Spindle speed in RPM (default: 10000).
    --tool_dia  Tool diameter in inches (default: 0.015in).
    --overlap   Tool overlap between passes as a fraction (default: 0.15).
    --xy_speed  XY cutting speed in inches per minute (default: 4.0ipm).
    --z_speed   Z cutting speed in inches per minute (default: 0.40ipm).

Notes:
- Sets the G-code units based on the SVG units, defaulting to millimeters if unrecognized.
- If the SVG file contains no rectangles, the script will terminate early with a message.

Dependencies:
- Python 3.x
- lxml library for parsing SVG files.

Raises:
- FileNotFoundError: If the input SVG file does not exist.
- ValueError: If the input file format is invalid or unsupported.
"""


parser = argparse.ArgumentParser(description="Convert SVG paths to G-code spirals")
parser.add_argument("infile", help="SVG file to process")
parser.add_argument("outfile", help="Output G-code filename")
parser.add_argument("--idle_z", type=float, default=1.000, help="Safe Z height (default: 1.000in)")
parser.add_argument("--pass_z", type=float, default=0.100, help="Passing Z height (default: 0.100in)")
parser.add_argument("--cut_z", type=float, default=-0.000, help="Cutting Z height (default: -0.000in)")
parser.add_argument("--spindle", type=int, default=10000, help="Spindle speed in RPM (default: 10000)")
parser.add_argument("--tool_dia", type=float, default=0.015, help="Tool diameter (default: 0.015in)")
parser.add_argument("--overlap", type=float, default=0.15, help="Tool overlap b/t passes as a fraction (default: 0.15)")
parser.add_argument("--xy_speed", type=float, default=4.0, help="XY cutting speed (default: 4.0ipm)")
parser.add_argument("--z_speed", type=float, default=0.40, help="Z cutting speed (default: 0.40ipm)")
# TODO: parser.add_argument("--units", type=str, default="", help="Units (in or mm) (default: determined by SVG)")

args = parser.parse_args()


class Config:
    def __init__(self):
        self.svg_units = None           # units of the SVG file
        self.idle_z = args.idle_z
        self.pass_z = args.pass_z
        self.cut_z = args.cut_z
        self.spindle = args.spindle
        self.tool_dia = args.tool_dia
        self.overlap = args.overlap
        self.xy_speed = args.xy_speed
        self.z_speed = args.z_speed
        # TODO: units = args.units

config = Config()


class Gcode:
    def __init__(self):
        self.units = ""             # "in" or "mm"
        self.coord_fmt = ".5f"      # coordinate format
        self.speed_fmt = ".4f"      # speed format
        self.comment_pos = 16       # position of comments

gcode = Gcode()


def parse_svg_rectangles(svg_file):
    """
    Parse an SVG file to extract rectangles from paths.

    Args:
        svg_file (str): Path to the SVG file.

    Returns:
        A list of tuples representing rectangles (x_min, y_min, width, height).
    """    
    rectangles = []

    try:
        tree = etree.parse(svg_file)
    except Exception as e:
        print(f"Error parsing SVG file: {e}")
        return []

    root = tree.getroot()
    namespaces = {'svg': 'http://www.w3.org/2000/svg'}  # Define the SVG namespace

    # Extract units from the width or height attributes
    width = root.get("width", None)
    height = root.get("height", None)

    if width and any(char.isalpha() for char in width):
        config.svg_units = ''.join(filter(str.isalpha, width))  # Extract units (e.g., "px", "mm", "cm")
    elif height and any(char.isalpha() for char in height):
        config.svg_units = ''.join(filter(str.isalpha, height))
    else:
        config.svg_units = "px"  # Default to pixels if no units are specified

    # Find all <path> elements
    for path in root.xpath('//svg:path', namespaces=namespaces):
        d = path.get('d')  # Get the 'd' attribute of the path
        if d:
            # Parse the path data to extract rectangle dimensions
            # Assuming the path outlines a rectangle
            commands = d.split()
            x_min = y_min = float('inf')
            x_max = y_max = float('-inf')

            i = 0
            while i < len(commands):
                command = commands[i]
                if command in {'M', 'L'}:  # Move or Line commands
                    i += 1  # Move to the next element for coordinates
                    if i < len(commands):
                        coords = commands[i].split(',')
                        if len(coords) == 2:  # Ensure there are two coordinates
                            try:
                                x, y = float(coords[0]), float(coords[1])
                                x_min = min(x_min, x)
                                x_max = max(x_max, x)
                                y_min = min(y_min, y)
                                y_max = max(y_max, y)
                            except ValueError:
                                print(f"Invalid coordinates in command: {command} {commands[i]}")
                                continue
                i += 1

            # Calculate rectangle dimensions if valid coordinates were found
            if x_min < float('inf') and y_min < float('inf'):
                width = x_max - x_min
                height = y_max - y_min
                rectangles.append((x_min, y_min, width, height))  # Use top-left corner
            else:
                print(f"Skipping invalid path: {d}")

    return rectangles

def sort_rectangles(rectangles):
    """
    Sort a list of rectangles using a nearest-neighbor approach to minimize travel distance.

    This function takes a list of rectangles, where each rectangle is represented as a tuple 
    (x_min, y_min, width, height). It sorts the rectangles in an order that minimizes the 
    travel distance between their centers, starting from the origin (0, 0).

    Args:
        rectangles (list of tuple): A list of rectangles, where each rectangle is defined 
        as (x_min, y_min, width, height).

    Returns:
        The list of rectangles sorted to minimize travel distance.
    """
    if not rectangles:
        return []

    sorted_rectangles = []
    remaining_rectangles = rectangles[:]

    # Start at the origin (0,0)
    current_x, current_y = 0, 0

    while remaining_rectangles:
        # Find the rectangle with the closest center to the current point
        closest_rect = min(
            remaining_rectangles,
            key=lambda rect: ((rect[0] + rect[2] / 2 - current_x) ** 2 + (rect[1] + rect[3] / 2 - current_y) ** 2) ** 0.5
        )
        sorted_rectangles.append(closest_rect)
        remaining_rectangles.remove(closest_rect)

        # Update the current point to the center of the last rectangle
        current_x = closest_rect[0] + closest_rect[2] / 2  # x_min + width / 2
        current_y = closest_rect[1] + closest_rect[3] / 2  # y_min + height / 2

    return sorted_rectangles

def generate_rectangular_spiral(x_min, y_min, x_max, y_max):
    """
    Generate a rectangular spiral path to fully cover the given rectangle area.

    This function creates a G-code path that spirals inward from the edges of the rectangle 
    towards the center, ensuring complete coverage.

    Args:
        x_min (float): The minimum x-coordinate of the rectangle.
        y_min (float): The minimum y-coordinate of the rectangle.
        x_max (float): The maximum x-coordinate of the rectangle.
        y_max (float): The maximum y-coordinate of the rectangle.

    Returns:
        A list of G-code commands representing the spiral path.
    """
    path_data = []

    x_mid, y_mid = x_max - x_min, y_max - y_min

    step_size = config.tool_dia * (1 - config.overlap)

    # Initial positions
    x_left = x_min + (config.tool_dia / 2)
    y_bottom = y_min + (config.tool_dia / 2)
    x_right = x_max - (config.tool_dia / 2)
    y_top = y_max - (config.tool_dia / 2)

    # Move to the starting point
    path_data.append(f"G0 X{x_left:{gcode.coord_fmt}} Y{y_bottom:{gcode.coord_fmt}}")

    # First loop: trace the full rectangle perimeter
    path_data.append(f"G1 X{x_right:{gcode.coord_fmt}} Y{y_bottom:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")
    path_data.append(f"G1 X{x_right:{gcode.coord_fmt}} Y{y_top:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")
    path_data.append(f"G1 X{x_left:{gcode.coord_fmt}} Y{y_top:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")
    path_data.append(f"G1 X{x_left:{gcode.coord_fmt}} Y{y_bottom:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")

    # Move inward for the spiral
    x_left += step_size
    x_right -= step_size
    y_bottom += step_size
    y_top -= step_size

    # # Jog to next part if we're not out of space in this rectangle
    # if (x_left < x_right and y_bottom < y_top):
    path_data.append(f"G1 X{x_left:{gcode.coord_fmt}} Y{y_bottom:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")

    first_pass = True
    while True:
        # Bottom edge, right edge
        path_data.append(f"G1 X{x_right:{gcode.coord_fmt}} Y{y_bottom:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")
        path_data.append(f"G1 X{x_right:{gcode.coord_fmt}} Y{y_top:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")

        # if this finished our fill, break the loop
        if ((x_right - x_left) < step_size) or ((y_top - y_bottom) < step_size):
            break

        # Top edge, left edge
        path_data.append(f"G1 X{x_left:{gcode.coord_fmt}} Y{y_top:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")
        y_bottom += step_size if y_bottom < (y_mid - step_size) else 0
        path_data.append(f"G1 X{x_left:{gcode.coord_fmt}} Y{y_bottom:{gcode.coord_fmt}} F{config.xy_speed:{gcode.speed_fmt}}")

        # if this finished our fill, break the loop
        if ((y_top - y_bottom) < step_size):
            break

        # Move inward
        x_left += step_size
        x_right -= step_size
        y_top -= step_size

    return path_data

def write_gcode_line(file, command="", comment=None):
    """
    Writes a single line of G-code to the specified file.
    """
    line = command
    if comment:
        line = f"{line:<{gcode.comment_pos}}; {comment}"
    file.write(line + "\n")

def write_gcode_spirals(outfile, rectangles):
    """
    Convert a list of rectangles to spiral paths and write them into a G-code file.

    This function takes a list of rectangles, where each is represented as a tuple 
    (x_min, y_min, width, height). Each is converted to a spiral path convering its area.
    The corresponding G-code commands are written to the specified output file, ensuring
    proper formatting and compatibility with the configured units.

    Args:
        outfile (str): The output G-code filename.
        rectangles (list of tuple): A list of rectangles, where each rectangle is defined 
        as (x_min, y_min, width, height).

    Returns:
        None
    """
    with open(outfile, 'w') as file:
        if gcode.units == "in":
            write_gcode_line(file, "G20", "Set units to inches")
        else:
            write_gcode_line(file, "G21", "Set units to millimeters")

        write_gcode_line(file, "G90", "Absolute positioning")
        write_gcode_line(file, f"G0 Z{config.idle_z:{gcode.coord_fmt}}")
        write_gcode_line(file, f"M3 S{config.spindle}", "Turn spindle on")

        write_gcode_line(file)
        write_gcode_line(file, f"G0 Z{config.pass_z:{gcode.coord_fmt}}")

        for rect in rectangles:
            x, y, w, h = rect
            x_min, y_min = x, y
            x_max, y_max = x + w, y + h
            print(f"Processing rectangle: ({x_min:{gcode.coord_fmt}}, {y_min:{gcode.coord_fmt}}), ({x_max:{gcode.coord_fmt}}, {y_max:{gcode.coord_fmt}})")
            spiral = generate_rectangular_spiral(x_min, y_min, x_max, y_max)
            write_gcode_line(file, spiral[0])  # Move to the starting point
            write_gcode_line(file, f"G1 Z{config.cut_z:{gcode.coord_fmt}} F{config.z_speed:{gcode.speed_fmt}}")
            for line in spiral[1:]:
                write_gcode_line(file, line)
            write_gcode_line(file, f"G0 Z{config.pass_z:{gcode.coord_fmt}}")
            write_gcode_line(file)

        write_gcode_line(file, "M5", "Turn spindle off")
        write_gcode_line(file, f"G0 Z{config.idle_z:{gcode.coord_fmt}}")
        write_gcode_line(file, f"G0 X0 Y0")
        write_gcode_line(file)

def convert_svg_to_spirals(infile, outfile):
    """
    Convert SVG paths to spiraling paths and save as G-code.

    This function processes an input SVG file, extracts rectangular paths, and converts them into spiraling paths. 
    The resulting G-code is saved to the specified output file.

    Args:
        infile (str): The path to the input SVG file containing rectangular paths.
        outfile (str): The path to the output file where the generated G-code will be saved.

    Workflow:
    1. Parses rectangles from the input SVG file.
    2. Sorts the rectangles by proximity to optimize the path.
    3. Sets the G-code units based on the SVG units, with a fallback to millimeters if unrecognized.
    4. Converts the rectangles into spiraling paths.
    5. Writes the generated G-code to the output file.

    Notes:
    - If the SVG file contains no rectangles, the function will terminate early with a message.
    - Units mismatches between the SVG and G-code are logged, and conversions may be required in future implementations.

    Raises:
        FileNotFoundError: If the input SVG file does not exist.
        ValueError: If the input file format is invalid or unsupported.

    """
    # Parse rectangles from the input SVG
    rectangles = parse_svg_rectangles(infile)

    print(f"SVG units: {config.svg_units}")
    if rectangles:
        x_min = min(rect[0] for rect in rectangles)
        y_min = min(rect[1] for rect in rectangles)
        x_max = max(rect[0] + rect[2] for rect in rectangles)
        y_max = max(rect[1] + rect[3] for rect in rectangles)
        print(f"{len(rectangles)} rectangles, overall dimensions: "
              f"({x_min:{gcode.coord_fmt}}, {y_min:{gcode.coord_fmt}}), ({x_max:{gcode.coord_fmt}}, {y_max:{gcode.coord_fmt}})")
    else:
        print("No rectangles found.")
        return

    # Sort rectangles by proximity
    rectangles = sort_rectangles(rectangles)

    gcode.units = config.svg_units
    if config.svg_units not in {"in", "mm"}:
        print(f"Warning: Unrecognized SVG units '{config.svg_units}', defaulting to millimeters.")
        gcode.units = "mm"

    # TODO: if (units == config.svg_units) or (units == ""):
    #           gcode.units = units = config.svg_units
    # TODO: if units = "mm" any arguments that were not entered by user have to be converted to mm from in
    # TODO: if gcode.units != config.svg_units, a conversion has to be done in generate_rectangular_spiral & write_gcode_spirals (?)

    # Convert rectangles to spirals and write them out
    write_gcode_spirals(outfile, rectangles)

    print(f"G-code saved as '{outfile}', units: {gcode.units}")

if __name__ == "__main__":

    if len(vars(args)) == 0:
        parser.print_help()
        exit(1)
    
    convert_svg_to_spirals(args.infile, args.outfile)