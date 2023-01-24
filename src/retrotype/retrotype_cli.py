"""
Imports Commodore BASIC type-in programs in various magazine formats,
checks for errors, and converts to an executable file for use with an
emulator or on original hardware.
"""

import argparse
import math
import sys
from argparse import RawTextHelpFormatter
from os import get_terminal_size
from typing import List

from retrotype.retrotype_lib import (
    Checksums,
    OutputFiles,
    TextListing,
    TokenizedLine,
)

SOURCE_CHOICES = ["ahoy1", "ahoy2", "ahoy3"]


def check_source(source: str) -> str:
    """Custom type for source argument for custom verbiage when argument
    error is encountered.
    """
    if source in SOURCE_CHOICES:
        return source
    source_string = "'" + "', '".join(SOURCE_CHOICES) + "'"
    raise argparse.ArgumentTypeError(
        f"invalid choice: '{source}'\n"
        "Magazine format not yet supported - "
        f"choose from {source_string}."
    )


def parse_args(argv):
    """Parses command line inputs and generate command line interface and
    documentation.
    """
    parser = argparse.ArgumentParser(
        description="A tokenizer for Commodore BASIC typein programs. Supports"
        "Ahoy magazine\nprograms for C64.",
        formatter_class=RawTextHelpFormatter,
        epilog="Notes for entering programs from Ahoy issues prior to "
        "November 1984:\n\n"
        "In addition to the special character codes contained in braces \n"
        "in the magazine, Ahoy also used a shorthand convention for \n"
        "specifying a key entry preceeded by either the Shift key or the \n"
        "Commodore key as follows:\n\n"
        "    - Underlined characters - preceed entry with Shift key\n"
        "    - Overlined characters - preceed entry with Commodore key\n\n"
        "Standard keyboard letters should be typed as follows for these "
        "two cases.\n"
        "    -{s A}, {s B}, {s *} etc.\n"
        "    -{c A}, {c B}, {c *}, etc.\n\n"
        "There are a few instances where the old hardware has keys not\n"
        "available on a modern keyboard or are otherwise ambiguous.\n"
        "Those should be entered as follows:\n"
        "    {EP} - British Pound symbol\n"
        "    {UP_ARROW} - up arrow symbol\n"
        "    {LEFT_ARROW} - left arrow symbol\n"
        "    {PI} - Pi symbol\n"
        "    {s RETURN} - shifted return\n"
        "    {s SPACE} - shifted space\n"
        "    {c EP} - Commodore-Bristish Pound symbol\n"
        "    {s UP_ARROW} - shifted up arrow symbol\n\n"
        "After the October 1984 issue, the over/under score representation\n"
        "was discontinued.  These special characters should be typed as\n"
        "listed in the magazines after that issue.\n\n",
    )

    parser.add_argument(
        "-l",
        "--loadaddr",
        type=str,
        nargs=1,
        required=False,
        metavar="load_address",
        default=["0x0801"],
        help="Specifies the target BASIC memory address when loading:\n"
        "- 0x0801 - C64 (default)\n"
        "- 0x1001 - VIC20 Unexpanded\n"
        "- 0x0401 - VIC20 +3K\n"
        "- 0x1201 - VIC20 +8K\n"
        "- 0x1201 - VIC20 +16\n"
        "- 0x1201 - VIC20 +24K\n",
    )

    parser.add_argument(
        "-s",
        "--source",
        choices=SOURCE_CHOICES,
        type=check_source,  # custom type instead of str
        nargs=1,
        required=False,
        metavar="source_format",
        default=["ahoy2"],
        help="Specifies the magazine source for conversion and checksum:\n"
        "ahoy1 - Ahoy magazine (Apr-May 1984)\n"
        "ahoy2 - Ahoy magazine (Jun 1984-Apr 1987) (default)\n"
        "ahoy3 - Ahoy magazine (May 1987-)\n",
    )

    parser.add_argument(
        "file_in",
        type=str,
        metavar="input_file",
        help="Specify the input file name including path.\n"
        "Note:  Output file will use input file basename with\n"
        "extension '.prg' for Commodore file format.",
    )

    return parser.parse_args(argv)


def print_checksums(ahoy_checksums: List[str], terminal_width: int) -> None:

    # Determine number of columns to print based on terminal window width
    columns = terminal_width // 12
    # Determine number of rows based on column count
    rows = math.ceil(len(ahoy_checksums) / columns)

    # Print each line number, code combination in matrix format
    for i in range(rows):
        for j in range(columns):
            indx = i + (j * rows)
            if indx < len(ahoy_checksums):
                prt_line = str(ahoy_checksums[indx][0])
                prt_code = str(ahoy_checksums[indx][1])
                left_space = 7 - len(prt_line) - len(prt_code)
                print(" " * left_space, prt_line, prt_code, " " * 2, end="")
        print(end="\n")

    print(f"\nLines: {len(ahoy_checksums)}\n")


def command_line_runner(argv=None, width=None):

    # call function to parse command line input arguments
    args = parse_args(argv)

    # call function to read input file lines
    tl = TextListing(args.file_in)
    try:
        raw_listing = tl.read_listing()
    except FileNotFoundError:
        print("File read failed - please check source file name and path.")
        sys.exit(1)

    # check each line to insure each starts with a line number
    # and that the line numbers are sequential.
    if sequence_message := tl.check_line_num_seq(raw_listing):
        print(sequence_message)
        sys.exit(1)

    # Check for loose brackets/braces
    if brace_message := tl.check_for_loose_braces(raw_listing):
        print(brace_message)
        sys.exit(1)

    # Create lines list converting to common special character codes in braces
    if args.source[0][:4] == "ahoy":
        lines_list = tl.ahoy_lines_list(raw_listing)
    else:
        # reserved for selecting future magazine formats
        sys.exit(1)  # pragma: no cover

    addr = int(args.loadaddr[0], 16)

    out_list = []
    ahoy_checksums = []

    for line in lines_list:
        # split each line into line number and remaining text
        (line_num, line_txt) = tl.split_line_num(line)

        tkln = TokenizedLine(line_txt)

        token_ln = []
        # add load address at start of first line only
        if addr == int(args.loadaddr[0], 16):
            token_ln.append(addr.to_bytes(2, "little"))
        byte_list = tkln.scan_manager()

        cs = Checksums(line_num, byte_list)

        # call checksum generator function to build list of tuples
        if args.source[0] == "ahoy1":
            ahoy_checksums.append((line_num, cs.ahoy1_checksum()))
        elif args.source[0] == "ahoy2":
            ahoy_checksums.append((line_num, cs.ahoy2_checksum()))
        elif args.source[0] == "ahoy3":
            ahoy_checksums.append((line_num, cs.ahoy3_checksum()))
        else:
            # reserved for selecting future magazine formats
            sys.exit(1)  # pragma: no cover

        addr = addr + len(byte_list) + 4

        token_ln.extend(
            (
                addr.to_bytes(2, "little"),
                line_num.to_bytes(2, "little"),
                byte_list,
            )
        )

        token_ln = [byte for sublist in token_ln for byte in sublist]

        out_list.append(token_ln)

    out_list.append([0, 0])

    bytes_out = [byte for sublist in out_list for byte in sublist]

    file_stem = args.file_in.split(".")[0]

    ofiles = OutputFiles(bytes_out, ahoy_checksums)

    # Write binary file compatible with Commodore computers or emulators
    ofiles.write_binary(f"{file_stem}.prg")

    # Write text file containing line numbers, checksums, and line count
    ofiles.write_checksums(f"{file_stem}.chk")

    # Print line checksums to terminal, formatted based on screen width
    print("Line Checksums:\n")
    if not width:
        width = get_terminal_size()[0]  # pragma: no cover
    print_checksums(ahoy_checksums, width)


if __name__ == "__main__":
    sys.exit(command_line_runner())  # pragma: no cover
