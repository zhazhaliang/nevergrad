# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import tempfile
from pathlib import Path
from unittest import TestCase
from typing import Tuple, List, Optional
import genty
import numpy as np
from ..common import testing
from . import instantiate
from .instantiate import LINETOKEN
from .instantiate import Placeholder


def test_symlink_folder_tree() -> None:
    path = Path(__file__).parents[2]
    with tempfile.TemporaryDirectory() as folder:
        instantiate.symlink_folder_tree(path, folder)


@genty.genty
class InstantiationTests(TestCase):

    def _test_uncomment_line(self, line: str, ext: str, expected: str) -> None:
        if isinstance(expected, str):
            output = instantiate.uncomment_line(line, ext)
            np.testing.assert_equal(output, expected)
        else:
            np.testing.assert_raises(expected, instantiate.uncomment_line, line, ext)

    # CAREFUL: avoid triggering errors if the module parses itself...
    # Note: 'bidule' is French for dummy widget
    @genty.genty_dataset(  # type: ignore
        nothing=("    bidule", ".py", "    bidule"),
        python=(f"    # {LINETOKEN} bidule", ".py", "    bidule"),
        not_starting_python=(f"x    # {LINETOKEN} bidule", ".py", RuntimeError),
        bad_python=("    // @" + "nevergrad@ bidule", ".py", RuntimeError),
        cpp=(f"  //{LINETOKEN}bidule", ".cpp", "  bidule"),
        matlab=(f"%{LINETOKEN}bidule", ".m", "bidule"),
        unknown=(f"// {LINETOKEN} bidule", ".unknown", RuntimeError),
    )
    def test_uncomment_line(self, line: str, ext: str, expected: str) -> None:
        self._test_uncomment_line(line, ext, expected)

    @genty.genty_dataset(  # type: ignore
        custom=(f"// {LINETOKEN} bidule", ".custom", "//", "bidule"),
        wrong_comment_chars=(f"// {LINETOKEN} bidule", ".custom", "#", RuntimeError),
    )
    def test_uncomment_line_custom_file_type(self, line: str, ext: str, comment: str, expected: str) -> None:
        instantiate.register_file_type(ext, comment)
        self._test_uncomment_line(line, ext, expected)
        del instantiate.COMMENT_CHARS[ext]

    @genty.genty_dataset(  # type: ignore
        with_clean_copy=(True,),
        without_clean_copy=(False,),
    )
    def test_folder_instantiator(self, clean_copy: bool) -> None:
        path = Path(__file__).parent / "examples"
        ifolder = instantiate.FolderInstantiator(path, clean_copy=clean_copy)
        testing.printed_assert_equal(ifolder.placeholders, [Placeholder("value1", "this is a comment"),
                                                            Placeholder("value2", None)])
        np.testing.assert_equal(len(ifolder.file_functions), 1)
        with ifolder.instantiate(value1=12, value2=110.) as tmp:
            with (tmp / "script.py").open("r") as f:
                lines = f.readlines()
        np.testing.assert_equal(lines[10], "value2 = 110.0\n")

    @genty.genty_dataset(  # type: ignore
        void=("bvcebsl\nsoefn", []),
        unique_no_comment=("bfseibf\nbsfei NG_VAR{machin}", [("machin", None)]),
        several=("bfkes\nsgrdgrgbdrkNG_VAR{truc|blublu}sehnNG_VAR{bidule}", [("truc", "blublu"), ("bidule", None)]),
    )
    def test_placeholder(self, text: str, name_comments: List[Tuple[str, Optional[str]]]) -> None:
        placeholders = Placeholder.finditer(text)
        testing.printed_assert_equal(placeholders, [Placeholder(*x) for x in name_comments])


def test_placeholder_substitution() -> None:
    text = "bfkes\nsgrdgrgbdrkNG_VAR{truc|blublu}sehn NG_VAR{bidule}"
    expected = "bfkes\nsgrdgrgbdrk#12#sehn 24"
    output = Placeholder.sub(text, truc="#12#", bidule=24)
    np.testing.assert_equal(output, expected)
    np.testing.assert_raises(KeyError, Placeholder.sub, text, truc="#12#")
    np.testing.assert_raises(RuntimeError, Placeholder.sub, text, truc="#12#", bidule=24, chouette=12)
    text = "bfkes\nsgrdgrgbdrkNG_VAR{truc|blublu}sehnNG_VAR{bidule}NG_VAR{bidule|bis}"
    np.testing.assert_raises(RuntimeError, Placeholder.sub, text, truc="#12#", bidule=24)


def test_file_text_function() -> None:
    path = Path(__file__).parent / "examples" / "script.py"
    filefunc = instantiate.FileTextFunction(path)
    testing.printed_assert_equal(filefunc.placeholders, [Placeholder("value1", "this is a comment"),
                                                         Placeholder("value2", None)])


def test_folder_function() -> None:
    folder = Path(__file__).parent / "examples"
    func = instantiate.FolderFunction(str(folder), ["python", "examples/script.py"], clean_copy=True)
    output = func(value1=98, value2=6)
    np.testing.assert_equal(output, 12)
