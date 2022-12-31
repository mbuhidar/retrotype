"""
Tools to support typing in Commodore BASIC programs, including support for
various magazine formats, checking for errors, and converting to an executable
format for use with an emulator or on original hardware.
"""

import re
from os import remove
from typing import List, Optional, Tuple

# import variables from module containing Commodore-to-magazine conversion maps
from retrotype.char_maps import (
    AHOY_TO_PETCAT,
    PETCAT_TOKENS,
    SHIFT_CMDRE_TOKENS,
    TOKENS_V2,
)


class TextListing:
    """
    Program listing support for import, error checking, and conversion of
    type-in Commodore BASIC type-in programs in various magazine formats.
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def read_listing(self) -> List[str]:
        """
        Opens and reads magazine source file, strips whitespace, and
        returns a list of lines converted to lowercase

        Args:
            filename (str): The file name of the magazine source file

        Returns:
            list: a list of strings for each non-blank line from the source
            file converted to lowercase
        """

        with open(self.filename) as file:
            lines = file.readlines()
            lower_lines = [
                line.rstrip().lower() for line in lines if line.strip()
            ]
        return lower_lines

    def check_line_num_seq(self, raw_listing: List[str]) -> Optional[str]:
        """Check each line in the program for lines that either do not start
           with a line number or start with an out of sequence line number.

        Args:
            lines_list (list): List of lines (str) in program.

        Returns:
            string: sequence error message text or None
        """

        # handle case where first line does not have a line number
        ln_num_buffer = [0]

        for line in raw_listing:
            try:
                line_no = self.split_line_num(line)[0]
                ln_num_buffer.append(line_no)

                if not ln_num_buffer[0] < ln_num_buffer[1]:
                    return (
                        f"Entry error after line {ln_num_buffer[0]} - "
                        "lines should be in sequential order.  Exiting."
                    )
                ln_num_buffer.pop(0)

            except ValueError:
                return (
                    f"Entry error after line {ln_num_buffer.pop(0)} - "
                    "each line should start with a line number.  Exiting."
                )
        return None

    def split_line_num(self, line: str) -> Tuple[int, str]:
        """Split each line into line number and remaining line text

        Args:
            line (str): Text of each line to split

        Returns:
            tuple consisting of:
                line number (int): Line number split from the beginning of line
                remaining text (str): Text for remainder of line with
                                        whitespace stripped
        """

        line = line.lstrip()
        acc = []
        while line and line[0].isdigit():
            acc.append(line[0])
            line = line[1:]

        return (int("".join(acc)), line.lstrip())

    def check_for_loose_braces(self, listing: List[str]) -> Optional[str]:
        """Check each line for loose brackets/braces

        Args:
            listing (list): List of lines (str) in program.

        Returns:
            If brace error: line number (str)
            If no error: None
        """

        for line in listing:
            # replace brackets with braces since both were used in listings
            line = line.replace("[", "{")
            line = line.replace("]", "}")

            # split each line on special character representations
            str_split = re.split(r"{\d+\s?\".[^{]*?\"}|{.[^{]*?}", line)

            # check for loose braces in each substring, return error indication
            for sub_str in str_split:
                loose_brace = re.search(r"\}|{", sub_str)
                if loose_brace:
                    bad_line = self.split_line_num(line)[0]
                    return (
                        f"Loose brace/bracket error in line: {bad_line}\n"
                        "Special characters should be enclosed in "
                        "braces/brackets.\n"
                        "Please check for unmatched single brace/bracket "
                        "in above line."
                    )

        return None

    def ahoy_lines_list(self, lines_list: List[str]) -> List[str]:
        """For each line in the program, convert Ahoy special characters to
           Petcat special characters.

        Args:
            lines_list (list): List of lines (str) in program.

        Returns:
            new_lines (list): List of new lines (str) after special characters
                                are converted from Ahoy to petcat format.
        """

        new_lines = []

        for line in lines_list:
            # replace brackets with braces since Ahoy used both over time
            line = line.replace("[", "{")
            line = line.replace("]", "}")

            # split each line on ahoy special characters
            str_split = re.split(r"{\d+\s?\".[^{]*?\"}|{.[^{]*?}", line)

            # create list of ahoy special character code strings
            code_split = re.findall(r"{\d+\s?\".+?\"}|{.+?}", line)

            new_codes = []

            # for each ahoy special character, append the petcat equivalent
            num = 0

            for item in code_split:
                if item.upper() in AHOY_TO_PETCAT:
                    new_codes.append(AHOY_TO_PETCAT[item.upper()])

                elif re.match(r"{\d+\s?\".+?\"}", item):
                    # Extract number of times to repeat special character
                    char_count = int(
                        re.search(r"\d+\b", item).group()  # type: ignore
                    )
                    # Get the string inside the brackets and strip quotes
                    char_code = re.search(
                        r"\".+?\"", item
                    ).group()[  # type: ignore
                        1:-1
                    ]
                    if char_code.upper() in AHOY_TO_PETCAT:
                        new_codes.append(AHOY_TO_PETCAT[char_code.upper()])

                        while char_count > 1:
                            new_codes.append(AHOY_TO_PETCAT[char_code.upper()])
                            str_split.insert(num + 1, "")
                            num += 1
                            char_count -= 1

                    else:
                        new_codes.append(char_code)
                        while char_count > 1:
                            new_codes.append(char_code)
                            str_split.insert(num + 1, "")
                            num += 1
                            char_count -= 1

                else:
                    new_codes.append(item)
                num += 1

            # add blank item to list of special characters prior to blending
            if new_codes:
                new_codes.append("")

                new_line: List[str] = []

                # piece the string segments and petcat codes back together
                for count in range(len(new_codes)):
                    new_line.extend((str_split[count], new_codes[count]))

            # handle case where line contained no special characters
            else:
                new_line = str_split
            new_lines.append("".join(new_line))

        return new_lines


class TokenizedLine:
    """
    Support for conversion of BASIC program lines by converting BASIC keywords,
    petcat special characters, or ascii characters to tokenized bytes.
    """

    def __init__(self, line_text: str) -> None:
        self.line_text = line_text

    def scan_manager(self) -> List[int]:
        """Manage scan process for each line for BASIC keywords, petcat special
           characters, or ascii characters, convert to tokenized bytes, and
           return remaining line segment after converted characters are removed

        Args:
            instance, ln (str): Text of each line segment to parse and convert

        Returns:
            byte_list (list): List of converted bytes created from keywords,
                special characters, and ASCII characters converted bytes
        """

        in_quotes = False
        in_remark = False
        byte_list = []

        while self.line_text:
            (byte, self.line_text) = self._scan(
                tokenize=not (in_quotes or in_remark)
            )
            byte_list.append(byte)
            if byte == ord('"'):
                in_quotes = not in_quotes
            if byte == 143:
                in_remark = True
        byte_list.append(0)
        return byte_list

    def _scan(self, tokenize: bool = True) -> Tuple[int, str]:
        """Scan beginning of each line for BASIC keywords, petcat special
           characters, or ascii characters, convert to tokenized bytes, and
           return remaining line segment after converted characters are removed

        Args:
            instance, ln (str): Text of each line segment to parse and convert
            tokenize (bool): Flag to indicate if start of line segment should
                be tokenized (False if line segment start is within quotes or
                after a REM statement)

        Returns:
            tuple consisting of:
                character/token value (int): Decimal value of ascii character
                    or tokenized word
                remainder of line (str): Text for remainder of line with
                    keyword, specical character, or alphanumeric character
                    stripped
        """

        # check if each line passed in starts with a petcat special character
        # if so, return value of token and line with token string removed
        for (token, value) in PETCAT_TOKENS:
            if self.line_text.startswith(token):
                return (value, self.line_text[len(token) :])

        # check if each line passed in starts with shifted or commodore special
        # character. if so, return value of (token, line), remove token string.
        for (token, value) in SHIFT_CMDRE_TOKENS:
            if self.line_text.startswith(token):
                return (value, self.line_text[len(token) :])

        # if tokenize flag is True (i.e. line beginning is not inside quotes or
        # after a REM statement), check if line starts with a BASIC keyword
        # if so, return value of token and line with BASIC keyword removed
        if tokenize:
            for (token, value) in TOKENS_V2:
                if self.line_text.startswith(token):
                    return (value, self.line_text[len(token) :])

        # for characters without token values, convert to unicode (ascii) value
        # and, for latin letters, shift values by -32 to account for difference
        # between ascii and petscii used by Commodore BASIC.
        # finally, return character value and line with character removed
        char_value = ord(self.line_text[0])
        if char_value >= 97 and char_value <= 122:
            char_value -= 32
        return (char_value, self.line_text[1:])


class Checksums:
    """
    Class for creation of Ahoy checksums from passed in byte lists to match the
    codes printed in the magazine for checking each line for typed in accuracy.
    """

    def __init__(self, line_num: int, byte_list: List[int]) -> None:
        self.line_num = line_num
        self.byte_list = byte_list

    def xor_to_checksum(self, xor_value: int) -> str:
        # get high nibble of xor_value
        high_nib = (xor_value & 0xF0) >> 4
        high_char_val = high_nib + 65  # 0x41
        # get low nibble of xor_value
        low_nib = xor_value & 0x0F
        low_char_val = low_nib + 65  # 0x41
        # return value of checksum
        return chr(high_char_val) + chr(low_char_val)

    def ahoy1_checksum(self) -> str:
        """
        Method to create Ahoy checksums from passed in byte list to match the
        codes printed in the magazine for checking each line for typed
        accuracy. Covers Ahoy Bug Repellent version for Mar-Apr 1984 issues.
        """

        next_value = 0

        for char_val in self.byte_list:
            # Detect spaces and ignore them
            if char_val == 32:
                continue
            next_value += char_val
            # left shift 1 bit and limit next_value to fit in one byte
            next_value = (next_value << 1) & 255

        xor_value = next_value

        return self.xor_to_checksum(xor_value)

    def ahoy2_checksum(self) -> str:
        """
        Method to create Ahoy checksums from passed in byte list to match the
        codes printed in the magazine for checking each line for typed in
        accuracy. Covers Ahoy Bug Repellent version for May 1984-Apr 1987
        issues.
        """

        xor_value = 0
        char_position = 1
        carry_flag = 1
        in_quotes = False

        for char_val in self.byte_list:

            # set carry flag to zero for char values less than ascii value for
            # quote character since assembly code for repellent sets carry flag
            # based on cmp 0x22 (decimal 34)

            carry_flag = 0 if char_val < 34 else 1

            # Detect quote symbol in line and toggle in-quotes flag
            if char_val == 34:
                in_quotes = not in_quotes

            # Detect spaces that are outside of quotes and ignore them, else
            # execute primary checksum generation algorithm
            if char_val == 32 and in_quotes is False:
                continue

            next_value = char_val + xor_value + carry_flag
            xor_value = next_value ^ char_position

            # limit next value to fit in one byte
            next_value = next_value & 255

            char_position = char_position + 1

        return self.xor_to_checksum(xor_value)

    def ahoy3_checksum(self) -> str:
        """
        Method to create Ahoy checksums from passed in line number and
        byte list to match the codes printed in the magazine for checking each
        line for typed in accuracy. Covers the last Ahoy Bug Repellent
        version introduced in May 1987.
        """

        xor_value = 0
        char_position = 0
        in_quotes = False

        line_low = self.line_num % 256
        line_hi = int(self.line_num / 256)

        byte_line = [line_low] + [line_hi] + self.byte_list

        for char_val in byte_line:

            # Detect quote symbol in line and toggle in-quotes flag
            if char_val == 34:
                in_quotes = not in_quotes

            # Detect spaces that are outside of quotes and ignore them, else
            # execute primary checksum generation algorithm
            if char_val == 32 and in_quotes is False:
                continue

            next_value = char_val + xor_value

            xor_value = next_value ^ char_position

            # limit next value to fit in one byte
            next_value = next_value & 255

            char_position = char_position + 1

        return self.xor_to_checksum(xor_value)


class OutputFiles:
    """
    Support for writing binary files readable on Commodore computers or
    emulators and writing checksum files for comparison to codes printed in
    the magazines.
    """

    def __init__(self, bytes_out: List[int], checksums_out: List[str]) -> None:
        self.bytes_out = bytes_out
        self.checksums_out = checksums_out

    def write_checksums(self, filename: str) -> None:
        output = []

        # Print each line number, code combination in matrix format
        for checksum in self.checksums_out:
            prt_line = str(checksum[0])
            prt_code = str(checksum[1])
            output.append(f"{prt_line} {prt_code}\n")

        output.append(f"\nLines: {len(self.checksums_out)}\n")

        with open(filename, "w") as f:
            for line in output:
                f.write(line)

    def write_binary(self, filename: str) -> None:
        """Write binary file readable on Commodore computers or emulators

        Args:
            filename (str): The file name of the file to write as binary
            int_list (list): List of integers to convert to binary bytes and
                output write to file

        Returns:
            None: Implicit return
        """

        print(f'Writing binary output file "{filename}"...\n')

        try:
            with open(filename, "xb") as file:
                for byte in self.bytes_out:
                    file.write(byte.to_bytes(1, byteorder="big"))
                print(f'File "{filename}" written successfully.\n')

        except FileExistsError:
            if self.confirm_overwrite(filename):
                remove(filename)
                self.write_binary(filename)
            else:
                print(f'File "{filename}" not overwritten.\n')

    def confirm_overwrite(self, filename) -> bool:

        overwrite = input(
            f'Output file "{filename}" already exists. '
            "Overwrite? (Y = yes) "
        )
        return overwrite.lower() == "y"


if __name__ == "__main__":
    print(TextListing.__dict__)  # pragma: no cover
