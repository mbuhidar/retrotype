import argparse
import contextlib
from io import StringIO

import pytest

from retrotype.retrotype_cli import (
    command_line_runner,
    parse_args,
    print_checksums,
)


@pytest.mark.parametrize(
    "argv, arg_valid",
    [
        (["infile.ahoy"], ["0x0801", "ahoy2", False, "infile.ahoy"]),
        (
            ["infile.ahoy", "-s", "ahoy1"],
            ["0x0801", "ahoy1", False, "infile.ahoy"],
        ),
        (
            ["infile.ahoy", "-l", "0x1001"],
            ["0x1001", "ahoy2", False, "infile.ahoy"],
        ),
        (["infile.ahoy", "-w"], ["0x0801", "ahoy2", True, "infile.ahoy"]),
        (
            ["infile.ahoy", "-s", "ahoy3", "-l", "0x1001", "-w"],
            ["0x1001", "ahoy3", True, "infile.ahoy"],
        ),
        (
            ["-s", "ahoy3", "infile.ahoy", "-l", "0x1001"],
            ["0x1001", "ahoy3", False, "infile.ahoy"],
        ),
    ],
)
def test_parse_args(argv, arg_valid):
    """
    Unit test to check that function parse_args() yields the correct list of
    arguments for a range of different command line input combinations.
    """
    args = parse_args(argv)
    arg_list = [args.loadaddr[0], args.source[0], args.wip, args.file_in]
    assert arg_list == arg_valid


@pytest.mark.parametrize(
    "ahoy_checksums, term_width, term_capture",
    [
        ([(11110, "AP")], 31, " 11110 AP   \n\nLines: 1\n\n"),
        (
            [
                (10, "HE"),
                (20, "PH"),
                (30, "IM"),
                (40, "CD"),
                (50, "OB"),
                (60, "OF"),
                (70, "OG"),
                (80, "NI"),
                (90, "DG"),
                (100, "IC"),
                (64000, "KK"),
            ],
            44,
            "    10 HE       50 OB       90 DG   \n    20 PH       60 OF      "
            "100 IC   \n    30 IM       70 OG    64000 KK   \n    40 CD       "
            "80 NI   \n\nLines: 11\n\n",
        ),
    ],
)
def test_print_checksums(capsys, ahoy_checksums, term_width, term_capture):
    """
    Unit test to check that function print_checksums() is propery creating
    lists for lines and codes to print in a matrix format.
    """
    print_checksums(ahoy_checksums, term_width)
    captured = capsys.readouterr()
    assert captured.out == term_capture


@pytest.mark.parametrize(
    "source, lines_list, term",
    [
        (
            "ahoy1",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\nFile '
            '"{d}/example.prg" written successfully.\n\nLine '
            "Checksums:\n\n    "
            "10 IA       20 NI   \n\nLines: 2\n\n",
        ),
        (
            "ahoy2",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\nFile '
            '"{d}/example.prg" written successfully.\n\nLine '
            "Checksums:\n\n    "
            "10 EO       20 PH   \n\nLines: 2\n\n",
        ),
        (
            "ahoy3",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\nFile '
            '"{d}/example.prg" written successfully.\n\nLine '
            "Checksums:\n\n    "
            "10 GC       20 PP   \n\nLines: 2\n\n",
        ),
    ],
)
def test_command_line_runner(tmp_path, capsys, source, lines_list, term):
    """
    End to end test to check that function command_line_runner() is properly
    generating the correct output for a given command line input.
    """
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "example.bas"
    p.write_text(lines_list)

    term_capture = term.format(d=d)

    argv = ["-s", source, str(p)]

    command_line_runner(argv, 40)

    captured = capsys.readouterr()
    assert captured.out == term_capture


@pytest.mark.parametrize(
    "source, lines_list, term",
    [
        (
            "ahoy1",
            '10 PRINT"HELLO"\n20 GOTO10',
            "File read failed - please check source file name and path.\n",
        ),
    ],
)
def test_command_line_runner_nofile(
    tmp_path, capsys, source, lines_list, term
):
    """
    End to end test to check that function command_line_runner() is properly
    generating the correct output for a given command line input.
    """

    term_capture = term

    argv = ["-s", source, "nofile"]

    try:
        command_line_runner(argv, 40)
    except SystemExit as e:
        assert isinstance(e.__context__, FileNotFoundError)
    else:
        raise ValueError("Exception not raised")  # pragma: no cover

    captured = capsys.readouterr()
    assert captured.out == term_capture


@pytest.mark.parametrize(
    "source, lines_list, term",
    [
        (
            "ahoyx",
            '10 PRINT"HELLO"\n20 GOTO10',
            "usage: __main__.py [-h] [-l load_address] "
            "[-s source_format] [-w] "
            "input_file\n"
            "__main__.py: error: argument -s/--source: invalid choice: "
            "'ahoyx'\n"
            "Magazine format not yet supported - "
            "choose from 'ahoy1', 'ahoy2', 'ahoy3'.\n",
        ),
        (
            "rand_source_input",
            '10 PRINT"HELLO"\n20 GOTO10',
            "usage: __main__.py [-h] [-l load_address] "
            "[-s source_format] [-w] "
            "input_file\n"
            "__main__.py: error: argument -s/--source: invalid choice: "
            "'rand_source_input'\n"
            "Magazine format not yet supported - "
            "choose from 'ahoy1', 'ahoy2', 'ahoy3'.\n",
        ),
    ],
)
def test_command_line_runner_err(tmp_path, capsys, source, lines_list, term):
    """
    Test for handling of invalid source inputs.  Part of end to end test to
    check that function command_line_runner() is properly generating the
    correct output for a given command line input.
    """
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "example.bas"
    p.write_text(lines_list)

    term_capture = term.format(d=d)

    argv = ["-s", source, str(p)]

    try:
        command_line_runner(argv, 40)
    except SystemExit as e:
        assert isinstance(e.__context__, argparse.ArgumentError)
    else:
        raise ValueError("Exception not raised")  # pragma: no cover

    captured = capsys.readouterr()
    assert captured.err == term_capture


@pytest.mark.parametrize(
    "source, lines_list, term",
    [
        (
            "ahoy1",
            ["10 OK", "20 OK", "5 OFF", "40 OK"],
            "Entry error after line 20 - lines should be in "
            "sequential order.  Exiting.\n",
        ),
        (
            "ahoy2",
            ["10 OK", "200 OFF", "30 OK", "40 OK"],
            "Entry error after line 200 - lines should be in "
            "sequential order.  Exiting.\n",
        ),
        (
            "ahoy3",
            ["10 OK", "200 OFF", "3 OFF", "40 OK"],
            "Entry error after line 200 - lines should be in "
            "sequential order.  Exiting.\n",
        ),
        (
            "ahoy2",
            ["100 OFF", "20 OK", "30 OK", "40 OK"],
            "Entry error after line 100 - lines should be in "
            "sequential order.  Exiting.\n",
        ),
        (
            "ahoy1",
            ["10 OK", "OFF", "30 OK", "40 OK"],
            "Entry error after line 10 - each line should start with a line "
            "number.  Exiting.\n",
        ),
        (
            "ahoy3",
            ["OFF", "20OK", "30 ON", "40 OK"],
            "Entry error after line 0 - each line should start with a line "
            "number.  Exiting.\n",
        ),
        (
            "ahoy1",
            ["20OK", "ON"],
            "Entry error after line 20 - each line should start with a line "
            "number.  Exiting.\n",
        ),
        (
            "ahoy1",
            ["20 OK", "10 ON"],
            "Entry error after line 20 - lines should be in "
            "sequential order.  Exiting.\n",
        ),
    ],
)
def test_command_line_runner_bad_line_sequence(
    tmp_path, capsys, source, lines_list, term
):
    """
    End to end test to check that function command_line_runner() is properly
    generating the correct output for a given command line input.
    """
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "example.bas"
    p.write_text("\n".join(lines_list))

    term_capture = term

    argv = ["-s", source, str(p)]

    with contextlib.suppress(SystemExit):
        command_line_runner(argv, 40)

    captured = capsys.readouterr()
    assert captured.out == term_capture


@pytest.mark.parametrize(
    "lines_list, term",
    [
        (
            ['10 print"hello"', "20 {goto10"],
            "Loose brace/bracket error in line: 20\n"
            "Special characters should be enclosed in braces/brackets.\n"
            "Please check for unmatched single brace/bracket in above "
            "line.\n",
        ),
        (
            ["5 {WH}CY}", '10 print"hello"'],
            "Loose brace/bracket error in line: 5\n"
            "Special characters should be enclosed in braces/brackets.\n"
            "Please check for unmatched single brace/bracket in above "
            "line.\n",
        ),
        (
            ["5 {WH{CY}", '10 print"hello"'],
            "Loose brace/bracket error in line: 5\n"
            "Special characters should be enclosed in braces/brackets.\n"
            "Please check for unmatched single brace/bracket in above "
            "line.\n",
        ),
        (
            ["20 [PURPLE[LEFT][YELLOW][CYAN][SS]"],
            "Loose brace/bracket error in line: 20\n"
            "Special characters should be enclosed in braces/brackets.\n"
            "Please check for unmatched single brace/bracket in above "
            "line.\n",
        ),
        (
            ["20 PURPLE][LEFT][YELLOW][CYAN][SS]"],
            "Loose brace/bracket error in line: 20\n"
            "Special characters should be enclosed in braces/brackets.\n"
            "Please check for unmatched single brace/bracket in above "
            "line.\n",
        ),
        (
            ['30 print"4"*"][5"4"][BR]"'],
            "Loose brace/bracket error in line: 30\n"
            "Special characters should be enclosed in braces/brackets.\n"
            "Please check for unmatched single brace/bracket in above "
            "line.\n",
        ),
        (
            ['20 print"[4"*"[5"4"][BR]"'],
            "Loose brace/bracket error in line: 20\n"
            "Special characters should be enclosed in braces/brackets.\n"
            "Please check for unmatched single brace/bracket in above "
            "line.\n",
        ),
    ],
)
def test_command_line_runner_loose_braces(tmp_path, capsys, lines_list, term):
    """
    End to end test to check that function command_line_runner() is properly
    generating the correct output for a given command line input.
    """
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "example.bas"
    p.write_text("\n".join(lines_list))

    term_capture = term

    argv = [str(p)]

    with contextlib.suppress(SystemExit):
        command_line_runner(argv, 40)

    captured = capsys.readouterr()
    assert captured.out == term_capture


@pytest.mark.parametrize(
    "user_entry, source, lines_list, term",
    [
        (
            "Y\n",
            "ahoy1",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\n'
            'Output file "{d}/example.prg" already exists. '
            "Overwrite? (Y = yes) "
            'Writing binary output file "{d}/example.prg"...\n\n'
            'File "{d}/example.prg" written successfully.\n\nLine '
            "Checksums:\n\n"
            "    10 IA       20 NI   \n\nLines: 2\n\n",
        ),
        (
            "y\n",
            "ahoy2",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\n'
            'Output file "{d}/example.prg" already exists. '
            "Overwrite? (Y = yes) "
            'Writing binary output file "{d}/example.prg"...\n\n'
            'File "{d}/example.prg" written successfully.\n\nLine '
            "Checksums:\n\n"
            "    10 EO       20 PH   \n\nLines: 2\n\n",
        ),
        (
            "y\n",
            "ahoy3",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\n'
            'Output file "{d}/example.prg" already exists. '
            "Overwrite? (Y = yes) "
            'Writing binary output file "{d}/example.prg"...\n\n'
            'File "{d}/example.prg" written successfully.\n\nLine '
            "Checksums:\n\n"
            "    10 GC       20 PP   \n\nLines: 2\n\n",
        ),
        (
            "N\n",
            "ahoy1",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\n'
            'Output file "{d}/example.prg" already exists. '
            "Overwrite? (Y = yes) "
            'File "{d}/example.prg" not overwritten.\n\nLine '
            "Checksums:\n\n"
            "    10 IA       20 NI   \n\nLines: 2\n\n",
        ),
        (
            "N\n",
            "ahoy2",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\n'
            'Output file "{d}/example.prg" already exists. '
            "Overwrite? (Y = yes) "
            'File "{d}/example.prg" not overwritten.\n\nLine Checksums:\n\n'
            "    10 EO       20 PH   \n\nLines: 2\n\n",
        ),
        (
            "no\n",
            "ahoy3",
            '10 PRINT"HELLO"\n20 GOTO10',
            'Writing binary output file "{d}/example.prg"...\n\n'
            'Output file "{d}/example.prg" already exists. '
            "Overwrite? (Y = yes) "
            'File "{d}/example.prg" not overwritten.\n\nLine Checksums:\n\n'
            "    10 GC       20 PP   \n\nLines: 2\n\n",
        ),
    ],
)
def test_command_line_runner_interactive(
    tmp_path, capsys, monkeypatch, user_entry, source, lines_list, term
):
    """
    Test for handling of command line interaction.  Part of end to end test to
    check that function command_line_runner() is properly generating the
    correct output for a given command line input.
    """
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "example.bas"
    p.write_text(lines_list)
    o = d / "example.prg"
    o.write_text("create the file")

    term_capture = term.format(d=d)

    argv = ["-s", source, str(p)]

    monkeypatch.setattr("sys.stdin", StringIO(user_entry))
    command_line_runner(argv, 40)
    captured = capsys.readouterr()
    assert captured.out == term_capture
