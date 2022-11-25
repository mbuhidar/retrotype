import re
from typing import List, Optional, Tuple

# import char_maps.py: Module containing Commodore to magazine conversion maps
from retrotype.char_maps import (PETCAT_TOKENS,
                                 SHIFT_CMDRE_TOKENS,
                                 TOKENS_V2,
                                 AHOY_TO_PETCAT,
                                 )


class TextListing():
    """
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def read_listing(self) -> List[str]:
        """
        Opens and reads magazine source, strips whitespace, and
        returns a list of lines converted to lowercase

        Args:
            filename (str): The file name of the magazine source file

        Returns:
            list: a list of strings for each non-blank line from the source file
            converted to lowercase
        """

        with open(self.filename) as file:
            lines = file.readlines()
            lower_lines = []
            for line in lines:
                if not line.strip():
                    continue
                lower_lines.append(line.rstrip().lower())
        return lower_lines

    def check_line_num_seq(self, raw_listing: List[str]) -> Optional[str]:
        """Check each line in the program that either does not start with a line
           number or starts with an out of sequence line number.

        Args:
            lines_list (list): List of lines (str) in program.

        Returns:
            string: sequence error message text or None
        """

        line_no = 0  # handles case where first line does not have a line number
        ln_num_buffer = [0]  # first popped after three line numbers are appended
        for line in raw_listing:
            try:
                line_no = self.split_line_num(line)[0]
                ln_num_buffer.append(line_no)

                if not ln_num_buffer[0] < ln_num_buffer[1]:
                    return f"Entry error after line {ln_num_buffer[0]} - lines should be in sequential order.  Exiting."
                ln_num_buffer.pop(0)

            except ValueError:
                return f"Entry error after line {line_no} - each line should start with a line number.  Exiting."
        return None

    def split_line_num(self, line: str) -> Tuple[int, str]:
        """Split each line into line number and remaining line text

        Args:
            line (str): Text of each line to split

        Returns:
            tuple consisting of:
                line number (int): Line number split from the beginning of line
                remaining text (str): Text for remainder of line with whitespace
                    stripped
        """

        line = line.lstrip()
        acc = []
        while line and line[0].isdigit():
            acc.append(line[0])
            line = line[1:]

        return (int(''.join(acc)), line.lstrip())

    def check_for_loose_braces(self, listing: List[str]) -> Optional[str]:
        """Check each line for loose brackets/braces

        Args:
            listing (list): List of lines (str) in program.

        Returns:
            Brace error: line number (str)
            No error: None
        """

        for line in listing:
            # replace brackets with braces since both were used
            line = line.replace('[', '{')
            line = line.replace(']', '}')

            # split each line on special characters
            str_split = re.split(r"{\d+\s?\".[^{]*?\"}|{.[^{]*?}", line)

            # check for loose braces in each substring, return error indication
            for sub_str in str_split:
                loose_brace = re.search(r"\}|{", sub_str)
                if loose_brace is not None:
                    return str(self.split_line_num(line)[0])

        return None 

    def ahoy_lines_list(self, lines_list: List[str]) -> List[str]:
        """For each line in the program, convert Ahoy special characters to Petcat
           special characters.

        Args:
            lines_list (list): List of lines (str) in program.

        Returns:
            new_lines (list): List of new lines (str) after special characters are
                                converted from Ahoy to petcat format.
        """

        new_lines = []

        for line in lines_list:
            # replace brackets with braces since Ahoy used both over time
            line = line.replace('[', '{')
            line = line.replace(']', '}')

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
                    char_count = int(re.search(r"\d+\b", item).group())
                    # Get the string inside the brackets and strip quotes
                    char_code = re.search(r"\".+?\"", item).group()[1:-1]

                    if char_code.upper() in AHOY_TO_PETCAT:
                        new_codes.append(AHOY_TO_PETCAT
                                         [char_code.upper()])

                        while char_count > 1:
                            new_codes.append(AHOY_TO_PETCAT
                                             [char_code.upper()])
                            str_split.insert(num + 1, '')
                            num += 1
                            char_count -= 1

                    else:
                        new_codes.append(char_code)
                        while char_count > 1:
                            new_codes.append(char_code)
                            str_split.insert(num + 1, '')
                            num += 1
                            char_count -= 1

                else:
                    new_codes.append(item)
                num += 1

            # add blank item to list of special characters prior to blending
            if new_codes:
                new_codes.append('')

                new_line = []

                # piece the string segments and petcat codes back together
                for count in range(len(new_codes)):
                    new_line.extend((str_split[count], new_codes[count]))

            # handle case where line contained no special characters
            else:
                new_line = str_split
            new_lines.append(''.join(new_line))

        return new_lines


class Checksums():
    pass


class Bytes():
    pass


if __name__ == '__main__':
    print(TextListing.__dict__)
