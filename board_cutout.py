import sys
import re
import argparse
from shapely.geometry import Polygon

Version = 0.1
Tolerance = 1e-8

"""
This script generates G-code for cutting out a PCB from a TL file describing its extents.

It processes an input TL (TopLayer) gcode file, identifies the overall geometry of the board and generates a gcode file to cutout the board. The input TL should have a solid edge (which will be where the copper is removed as part of the TopLayer run). This program follows that edge shape and allows for a margin between that edge and the cut. 

Usage:
    python board_cutout.py <infile> <outfile> [options]

Arguments:
    infile          TL file for board geometry reference.
    outfile         Output G-code filename.

Options:
    --tl_tool_dia   TL file tool diameter (default: 0.015in, 30deg V-bit)
    --safe_z        Safe Z height (default: 0.500in)
    --pass_z        Passing Z height (default: 0.050in)
    --tab_depth     Depth to start leaving tabs (default: -0.036in)
    --tab_size      Size of tab holding board (default: 0.150in)
    --spindle       Spindle speed in RPM (default: 10000)
    --tool_dia      Tool diameter used to cut (default: 0.059in = 1.5mm endmill)
    --margin        Margin of board to leave around edge (default: 0.000in)
    --xy_speed      XY cutting speed (default: 4.0ipm)
    --z_speed       Z cutting speed (default: 2.0ipm)
    --z_cut         Cutting depth per pass (default: -0.006in)
    --depth         Total depth of cutout (default: -0.066in)

Notes:
- The script expects the TL file to contain G1/G01 commands for geometry extraction.
- Exits with an error if no geometry is found.

Dependencies:
- Python 3.x
"""

parser = argparse.ArgumentParser(description=f"Generate gcode for cutting-out a PCB from a TL file describing its extents (v{Version})")
parser.add_argument("infile", help="TL file for board geometry reference")
parser.add_argument("outfile", help="Output G-code filename")
parser.add_argument("--tl_tool_dia", type=float, default=0.015, help="TL file tool diameter (default: 0.015in, 30deg V-bit)")
parser.add_argument("--safe_z", type=float, default=0.500, help="Safe Z height (default: 0.500in)")
parser.add_argument("--pass_z", type=float, default=0.050, help="Passing Z height (default: 0.050in)")
parser.add_argument("--tab_depth", type=float, default=-0.036, help="Depth to start leaving tabs (default: -0.036in)")
parser.add_argument("--tab_size", type=float, default=0.150, help="Size of tab holding board (default: 0.150in)")
parser.add_argument("--spindle", type=int, default=10000, help="Spindle speed in RPM (default: 10000)")
parser.add_argument("--tool_dia", type=float, default=0.059, help="Tool diameter used to cut (default: 0.059in = 1.5mm endmill)")
parser.add_argument("--margin", type=float, default=0.000, help="Margin of board to leave around edge (default: 0.000in)")
parser.add_argument("--xy_speed", type=float, default=4.0, help="XY cutting speed (default: 4.0ipm)")
parser.add_argument("--z_speed", type=float, default=2.0, help="Z cutting speed (default: 2.0ipm)")
parser.add_argument("--z_cut", type=float, default=-0.006, help="Cutting depth per pass (default: -0.006in)")
parser.add_argument("--depth", type=float, default=-0.066, help="Total depth of cutout (default: -0.066in)")
# TODO: parser.add_argument("--units", type=str, default="", help="Units (in or mm) (default: in)")

args = parser.parse_args()

def build_cmdline_str(argv):
    """
    Build a list of strings representing the command-line call, each <= 80 chars,
    not splitting arguments. Exclude outfile argument.
    """
    cmdline_str = []
    current = ""
    for arg in argv[3:]:
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

class Gcode:
    def __init__(self):
        self.units = ""             # "in" or "mm"
        self.coord_fmt = " .5f"     # coordinate format
        self.speed_fmt = ".4f"      # speed format
        self.rpm_fmt = "d"          # rpm format
        self.comment_pos = 26       # position of comments

gcode = Gcode()

class BoardGeometry:
    def __init__(self, outline_points):
        self.outline = outline_points  # List of (x, y) tuples

    @property
    def xs(self):
        return [x for x, _ in self.outline]

    @property
    def ys(self):
        return [y for _, y in self.outline]

    @property
    def extents(self):
        return (min(self.xs), max(self.xs), min(self.ys), max(self.ys))

    def offset(self, offset_value):
        """
        Returns a new BoardGeometry instance with the outline polyline offset outward by 'offset'.
        """
        poly = Polygon(self.outline)
        buffered = poly.buffer(offset_value)
        new_outline = list(buffered.exterior.coords)

        # Reorder the list so the point closest to origin is first
        min_idx = min(range(len(new_outline)), key=lambda i: new_outline[i][0]**2 + new_outline[i][1]**2)
        n = len(new_outline)
        idx = min_idx
        for _ in range(n):
            curr = new_outline[idx]
            next_idx = (idx + 1) % n
            nxt = new_outline[next_idx]
            if (abs(curr[0] - nxt[0]) < Tolerance) ^ (abs(curr[1] - nxt[1]) < Tolerance):
                break
            idx = (idx + 1) % n

        reordered_outline = new_outline[idx:] + new_outline[:idx]
        return BoardGeometry(reordered_outline)

    def print_extents(self, gcode):
        print("\nBoard extents:")
        print(f" X: {min(self.xs):{gcode.coord_fmt}} to {max(self.xs):{gcode.coord_fmt}}")
        print(f" Y: {min(self.ys):{gcode.coord_fmt}} to {max(self.ys):{gcode.coord_fmt}}")        

    def get_cutout(self, tool_dia, margin):
        return self.offset(tool_dia / 2 + margin)

    def extract_corner(self, corner=0, tab_size=0.150, tol=Tolerance):
        """
        Returns a list of (x, y) points describing:
        - a corner segment of the cutout outline including parts of adjacent edges and the intervening corner shape
        - tab_size is excluded in the middle of each orthogonal edge
        corner is 0=bottom-left, 1=top-left, 2=top-right, 3=bottom-right
        Assumes cutout is CW and closed.
        """
        # Find cutout bounds
        #xs, ys = zip(*self.outline)
        min_x, min_y = min(self.xs), min(self.ys)
        max_x, max_y = max(self.xs), max(self.ys)

        # find tab coordinates
        tab_x = (max_x - min_x - tab_size)/2
        tab_y = (max_y - min_y - tab_size)/2

        start_xy = [
            (min_x + tab_x, min_y        ),
            (min_x,         max_y - tab_y),
            (max_x - tab_x, max_y        ),
            (max_x,         min_y + tab_y)
        ]

        end_xy = [
            (min_x,         min_y + tab_y),
            (min_x + tab_x, max_y        ),
            (max_x,         max_y - tab_y),
            (max_x - tab_x, min_y        )
        ]

        points = []
        points.append(start_xy[corner])

        def walk_edge(idx, loop_condition):
            x, y = self.outline[idx]
            while loop_condition(x, y):
                points.append((x, y))
                idx = (idx + 1) % len(self.outline)
                x, y = self.outline[idx]

        # bottom-left and top-right corners (starting on a horizontal edge)
        if corner in [0, 2]:
            idx = next(i for i, (_, y) in enumerate(self.outline) if abs(y - start_xy[corner][1]) <= tol)
            x, y = self.outline[idx]

            # bottom-left
            if corner == 0:
                if x > start_xy[corner][0]:
                    idx = (idx + 1) % len(self.outline)
                walk_edge(idx, lambda x, y: abs(x - min_x) > tol)

            # top-right
            else:
                if x < start_xy[corner][0]:
                    idx = (idx + 1) % len(self.outline)
                walk_edge(idx, lambda x, y: abs(x - max_x) > tol)
        
        # top-left and bottom-right corners (starting on a vertical edge)
        else:
            idx = next(i for i, (x, _) in enumerate(self.outline) if abs(x - start_xy[corner][0]) <= tol)
            x, y = self.outline[idx]

            # top-left
            if corner == 1:
                if y < start_xy[corner][1]:
                    idx = (idx + 1) % len(self.outline)
                walk_edge(idx, lambda x, y: abs(y - max_y) > tol)

            # bottom-right
            else:
                if y > start_xy[corner][1]:
                    idx = (idx + 1) % len(self.outline)
                walk_edge(idx, lambda x, y: abs(y - min_y) > tol)

        points.append(end_xy[corner])
        return points

    def write_gcode(self, filename, args, gcode):
        """Write the G-code cutout file for this geometry."""

        def write_gcode_line(file, command="", comment=None):
            """Writes a gcode line to the output file."""
            line = command
            if comment:
                line = f"{line:<{gcode.comment_pos}}; {comment}"    
            file.write(line + "\n")
            return line

        with open(filename, "w") as file:
            file.write("\n")
            write_gcode_line(file, "G20", "inches")
            write_gcode_line(file, "G90", "absolute coordinates")
            write_gcode_line(file, "G94", "units per minute feedrates")

            # comment block
            file.write("\n")
            file.write("; Args:\n")

            for line in build_cmdline_str(sys.argv):
                file.write("; " + line + "\n")
            file.write("\n")
            file.write("; Board extents:\n")
            file.write(f"; X: {min(self.xs):{gcode.coord_fmt}} to {max(self.xs):{gcode.coord_fmt}}\n")
            file.write(f"; Y: {min(self.ys):{gcode.coord_fmt}} to {max(self.ys):{gcode.coord_fmt}}\n")
            
            file.write("\n")
            file.write(f"G00 Z{args.safe_z:{gcode.coord_fmt}}\n")

            # Move to first point (rapid)
            first_x, first_y = self.outline[0]
            write_gcode_line(file, f"G00 X{first_x:{gcode.coord_fmt}} Y{first_y:{gcode.coord_fmt}}", "Move to start of cutout")
            file.write(f"M03 S{args.spindle:{gcode.rpm_fmt}}\n")
            file.write(f"G00 Z{args.pass_z:{gcode.coord_fmt}}\n")

            # Cutout pattern down to tab_depth in steps of z_cut
            z = 0
            while z > args.tab_depth:
                file.write("\n")
                file.write(f"; Z = {z:{gcode.coord_fmt}} cut\n")
                file.write(f"G01 Z{z:{gcode.coord_fmt}} F{args.z_speed:{gcode.speed_fmt}}\n")
                file.write(f"F{args.xy_speed:{gcode.speed_fmt}}\n")
                for x, y in self.outline[1:]:
                    file.write(f"G01 X{x:{gcode.coord_fmt}} Y{y:{gcode.coord_fmt}}\n")
                file.write(f"G01 X{first_x:{gcode.coord_fmt}} Y{first_y:{gcode.coord_fmt}}\n")
                z = z + args.z_cut

            # Cutout each of the 4 corners leaving the 4 tabs, tab_size in the middle of each outline side
            for corner in range(4):
                corner_poly = self.extract_corner(corner, args.tab_size)
                file.write(f"\n; Corner {corner+1} cut\n")
                file.write(f"G00 Z{args.pass_z:{gcode.coord_fmt}}\n")
                first_x, first_y = corner_poly[0]
                write_gcode_line(file, f"G00 X{first_x:{gcode.coord_fmt}} Y{first_y:{gcode.coord_fmt}}", "Move to corner start")
                file.write(f"G00 Z{args.tab_depth:{gcode.coord_fmt}}\n")

                direction = 1
                z = args.tab_depth
                while z > args.depth:
                    file.write("\n")
                    file.write(f"; Z = {z:{gcode.coord_fmt}} cut\n")
                    file.write(f"G01 Z{z:{gcode.coord_fmt}} F{args.z_speed:{gcode.speed_fmt}}\n")
                    file.write(f"F{args.xy_speed:{gcode.speed_fmt}}\n")

                    iterable = corner_poly[1:] if direction == 1 else corner_poly[-2::-1]
                    for x, y in iterable:
                        file.write(f"G01 X{x:{gcode.coord_fmt}} Y{y:{gcode.coord_fmt}}\n")
                    direction *= -1
                    z = z + args.z_cut
                
            # Return to a safe position
            file.write("\n")
            write_gcode_line(file, f"G00 Z{args.safe_z:{gcode.coord_fmt}}", "Return to safe position")
            file.write("G00 X0Y0\n")
            file.write("M05\n")

def read_gcode_geometry(filename):
    # read board gcode file
    with open(filename, 'r') as f:
        gcode_lines = f.readlines()

    # Identify geometry block: first and last G1/G01 line
    geometry_start = None
    geometry_end = None
    for idx, line in enumerate(gcode_lines):
        if 'G1' in line or 'G01' in line:
            if geometry_start is None:
                geometry_start = idx
            geometry_end = idx

    return gcode_lines[geometry_start:geometry_end+1]

def find_board_outline(geometry_block):
    """
    Extracts the closed loop with the largest area (the board outline) from the geometry_block.
    Returns a list of (x, y) tuples representing the outline.
    """
    def extract_xy(line):
        x_pattern = re.compile(r'X([-+]?[0-9]*\.?[0-9]+)')
        y_pattern = re.compile(r'Y([-+]?[0-9]*\.?[0-9]+)')
        x_match = x_pattern.search(line)
        y_match = y_pattern.search(line)
        if x_match and y_match:
            return float(x_match.group(1)), float(y_match.group(1))
        return None

    def polygon_area(points):
        """Calculate the signed area of a polygon given as a list of (x, y) tuples."""
        area = 0.0
        n = len(points)
        for i in range(n):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % n]
            area += (x1 * y2) - (x2 * y1)
        return abs(area) / 2.0

    outlines = []
    current = []
    current_points = []
    start_xy = None

    for line in geometry_block:
        if ('G1' in line or 'G01' in line):
            xy = extract_xy(line)
            if xy:
                if not current:
                    start_xy = xy
                    current.append(line)
                    current_points = [xy]
                else:
                    current.append(line)
                    current_points.append(xy)
                    # Check if closed loop (returns to start)
                    if abs(xy[0] - start_xy[0]) < 1e-5 and abs(xy[1] - start_xy[1]) < 1e-5 and len(current) > 2:
                        outlines.append((list(current), list(current_points)))
                        current = []
                        current_points = []
                        start_xy = None
                continue
        if current:
            # End of a possible outline
            if len(current) > 2:
                outlines.append((list(current), list(current_points)))
            current = []
            current_points = []
            start_xy = None

    # If any outline left at end
    if current and len(current) > 2:
        outlines.append((list(current), list(current_points)))

    # Return the outline with the largest area, offset by TL tool radius
    if outlines:
        largest = max(outlines, key=lambda tup: polygon_area(tup[1]))
        return largest[1]
    else:
        return []

if __name__ == "__main__":

    if args.z_cut > 0:
        print("z_cut must be < 0")
        sys.exit(1)

    # get board outline from file, offset by tool radius
    geometry_block = read_gcode_geometry(args.infile)
    outline = find_board_outline(geometry_block)
    board = BoardGeometry(outline).offset(args.tl_tool_dia / 2)
    board.print_extents(gcode)

    # create the cutout pattern and write it
    cutout = board.get_cutout(args.tool_dia, args.margin)
    cutout.write_gcode(args.outfile, args, gcode)

    print()
    print(f"G-code saved as '{args.outfile}'")
    print()
