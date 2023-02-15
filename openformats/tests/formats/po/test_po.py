import unittest
import itertools

from openformats.exceptions import ParseError
from openformats.formats.po import PoHandler
from openformats.strings import OpenString
from openformats.tests.formats.common import CommonFormatTestMixin
from openformats.tests.utils.strings import strip_leading_spaces, generate_random_string


class PoTestCase(CommonFormatTestMixin, unittest.TestCase):
    HANDLER_CLASS = PoHandler
    TESTFILE_BASE = "openformats/tests/formats/po/files"

    def setUp(self):
        super(PoTestCase, self).setUp()
        self.handler = PoHandler()
        self.order_generator = itertools.count()

    def _create_openstring(self, pluralized, extra_context=None):
        context_dict = extra_context if extra_context is not None else {}
        context_dict.update(
            {"order": next(self.order_generator), "pluralized": pluralized}
        )
        key = generate_random_string()
        if pluralized:
            key = ":".join([key, generate_random_string()])

        openstring = OpenString(
            key,
            {0: generate_random_string(), 1: generate_random_string()}
            if pluralized
            else generate_random_string(),
            **context_dict
        )
        openstring.string_hash
        return openstring

    def test_openstring_has_all_fields(self):
        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""
            "Content-Type: text/plain; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"
            "Language: en\n"
            "Plural-Forms: nplurals=2; plural=(n != 1);\n"

            #  translator-comments1
            #  translator-comments2
            #. extracted-comments1
            #. extracted-comments2
            #: validators.py:9
            #: validators.py:11
            #, python-format
            #, another-flag
            msgid "metest"
            msgstr "msgstr1"
        """
        )
        template, stringset = self.handler.parse(source)
        expected_comment = (
            "extracted-comments1\nextracted-comments2\n"
            " translator-comments1\n translator-comments2"
        )
        self.assertEqual(len(stringset), 1)
        self.assertEqual(stringset[0].developer_comment, expected_comment)
        self.assertEqual(stringset[0].occurrences, "validators.py:9, validators.py:11")
        self.assertEqual(stringset[0].flags, "python-format, another-flag")

    def test_compiled_includes_all_with_obsoleted_strings(self):
        """
        Test that the existence of obsoleted strings in the po file
        marked with #~ does not cause strings after the obsoleted ones
        to be missing from the compiled file.
        """
        string1 = self._create_openstring(False)
        string2 = self._create_openstring(False)
        string3 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            #~ msgid "{s2_key}"
            #~ msgstr "{s2_str}"

            msgid "{s3_key}"
            msgstr "{s3_str}"
        """.format(
                **{
                    "s1_key": string1.key,
                    "s1_str": string1.string,
                    "s2_key": string2.key,
                    "s2_str": string2.string,
                    "s3_key": string3.key,
                    "s3_str": string3.string,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1, string2, string3])

        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"

                #~ msgid "{s2_key}"
                #~ msgstr "{s2_str}"

                msgid "{s3_key}"
                msgstr "{s3_str}"
                """.format(
                    **{
                        "s1_key": string1.key,
                        "s1_str": string1.string,
                        "s2_key": string2.key,
                        "s2_str": string2.string,
                        "s3_key": string3.key,
                        "s3_str": string3.string,
                    }
                )
            ),
        )

    def test_removes_untranslated_non_pluralized(self):
        string1 = self._create_openstring(False)
        string2 = self._create_openstring(False)
        string3 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            msgid "{s2_key}"
            msgstr "{s2_str}"

            msgid "{s3_key}"
            msgstr "{s3_str}"
        """.format(
                **{
                    "s1_key": string1.key,
                    "s1_str": string1.string,
                    "s2_key": string2.key,
                    "s2_str": string2.string,
                    "s3_key": string3.key,
                    "s3_str": string3.string,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1, string3])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"

                msgid "{s3_key}"
                msgstr "{s3_str}"
                """.format(
                    **{
                        "s1_key": string1.key,
                        "s1_str": string1.string,
                        "s3_key": string3.key,
                        "s3_str": string3.string,
                    }
                )
            ),
        )

    def test_removes_untranslated_pluralized(self):
        string1 = self._create_openstring(True)
        keys1 = string1.key.split(":")
        string2 = self._create_openstring(True)
        keys2 = string2.key.split(":")
        string3 = self._create_openstring(True)
        keys3 = string3.key.split(":")
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgid_plural "{s1_key_plural}"
            msgstr[0] "{s1_str_singular}"
            msgstr[1] "{s1_str_plural}"

            msgid "{s2_key}"
            msgid_plural "{s2_key_plural}"
            msgstr[0] "{s2_str_singular}"
            msgstr[1] "{s2_str_plural}"

            msgid "{s3_key}"
            msgid_plural "{s3_key_plural}"
            msgstr[0] "{s3_str_singular}"
            msgstr[1] "{s3_str_plural}"
        """.format(
                **{
                    "s1_key": keys1[0],
                    "s1_key_plural": keys1[1],
                    "s1_str_singular": string1.string[0],
                    "s1_str_plural": string1.string[1],
                    "s2_key": keys2[0],
                    "s2_key_plural": keys2[1],
                    "s2_str_singular": string2.string[0],
                    "s2_str_plural": string2.string[1],
                    "s3_key": keys3[0],
                    "s3_key_plural": keys3[1],
                    "s3_str_singular": string3.string[0],
                    "s3_str_plural": string3.string[1],
                }
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1, string3])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgid_plural "{s1_key_plural}"
                msgstr[0] "{s1_str_singular}"
                msgstr[1] "{s1_str_plural}"

                msgid "{s3_key}"
                msgid_plural "{s3_key_plural}"
                msgstr[0] "{s3_str_singular}"
                msgstr[1] "{s3_str_plural}"
                """.format(
                    **{
                        "s1_key": keys1[0],
                        "s1_key_plural": keys1[1],
                        "s1_str_singular": string1.string[0],
                        "s1_str_plural": string1.string[1],
                        "s3_key": keys3[0],
                        "s3_key_plural": keys3[1],
                        "s3_str_singular": string3.string[0],
                        "s3_str_plural": string3.string[1],
                    }
                )
            ),
        )

    def test_not_source_removes_untranslated_on_upload(self):
        string1 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            msgid "a_random_key"
            msgstr " "
        """.format(
                **{"s1_key": string1.key, "s1_str": string1.string}
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"
                """.format(
                    **{"s1_key": string1.key, "s1_str": string1.string}
                )
            ),
        )

    def test_duplicated_text_is_not_confused(self):
        string1 = self._create_openstring(False)
        source = strip_leading_spaces(
            """
            msgctxt ""
            msgid "{s1_key}"
            msgstr "{s1_key}"

            msgctxt "t2"
            msgid "{s1_key}"
            msgstr "{s1_key}"
        """.format(
                **{
                    "s1_key": string1.key,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgctxt ""
                msgid "{s1_key}"
                msgstr "{s1_str}"
            """.format(
                    **{"s1_key": string1.key, "s1_str": string1.string}
                )
            ),
        )

    def test_fuzzy_flag_removes_entry_but_keeps_strings(self):
        string1 = self._create_openstring(False)
        string2 = self._create_openstring(False, extra_context={"fuzzy": True})
        source = strip_leading_spaces(
            """
            #

            msgid ""
            msgstr ""

            msgid "{s1_key}"
            msgstr "{s1_str}"

            #, fuzzy
            msgid "{s2_key}"
            msgstr "{s2_str}"
        """.format(
                **{
                    "s1_key": string1.key,
                    "s1_str": string1.string,
                    "s2_key": string2.key,
                    "s2_str": string2.string,
                }
            )
        )
        template, stringset = self.handler.parse(source)
        compiled = self.handler.compile(template, [string1])
        self.assertEqual(
            compiled,
            strip_leading_spaces(
                """# \nmsgid ""
                msgstr ""

                msgid "{s1_key}"
                msgstr "{s1_str}"
                """.format(
                    **{"s1_key": string1.key, "s1_str": string1.string}
                )
            ),
        )

    def test_only_keys_error(self):
        self._test_parse_error(
            """
            msgid "msgid1"
            msgstr ""

            msgid "msgid2"
            msgstr "msgstr2"
            """,
            "A non-empty msgstr was found on the entry with msgid 'msgid2'. Remove and "
            "try again",
            parse_kwargs={"is_source": True},
        )

        self._test_parse_error(
            """
            msgid "msgid1"
            msgid_plural "msgid_plural1"
            msgstr[0] ""
            msgstr[1] ""

            msgid "msgid2"
            msgstr "msgstr2"
            """,
            "A non-empty msgstr was found on the entry with msgid 'msgid2'. Remove and "
            "try again",
            parse_kwargs={"is_source": True},
        )

    def test_only_values_error(self):
        self._test_parse_error(
            """
            msgid "msgid1"
            msgstr "msgstr1"

            msgid "msgid2"
            msgstr ""
            """,
            "The entry with msgid 'msgid2' includes an empty msgstr. Provide a value "
            "and try again",
            parse_kwargs={"is_source": True},
        )

    def test_msgstr_in_plural_entry(self):
        self._test_parse_error(
            """
            msgid "p1"
            msgid_plural "p2"
            msgstr "msgstr"
            """,
            "An unexpected msgstr was found on the pluralized entry with "
            "msgid 'p1' and msgid_plural 'p2'",
        )

    def test_pluralized_msgstr_in_non_pluralized_entry(self):
        self._test_parse_error(
            """
            msgid "p1"
            msgstr[0] "StringPlural1"
            msgstr[1] "StringsPlural2"
            """,
            "Found unexpected msgstr[*] on the non pluralized entry with msgid 'p1'",
        )

    def test_empty_msgid(self):
        self._test_parse_error(
            """
            msgid ""
            msgstr ""

            msgid ""
            msgstr "Not a plural"
            """,
            "Found empty msgid.",
        )

    def test_duplicate_keys(self):
        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgid "p1"
                msgstr "1"

                msgid "p1"
                msgstr "2"
            """,
            "A duplicate msgid was detected (p1). Use a unique "
            "msgid or add a msgctxt to differentiate",
        )

        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgctxt "t1"
                msgid "p1"
                msgstr "1"

                msgctxt "t1"
                msgid "p1"
                msgstr "2"
            """,
            "A duplicate msgid was detected (p1). Use a unique msgid or a unique "
            "msgctxt to differentiate (the existing msgctxt 't1' is a duplicate one)",
        )

        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "1"
                msgstr[1] "2"

                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "3"
                msgstr[1] "4"
            """,
            "A duplicate (msgid, msgid_plural) combination was "
            "detected (p1, p2). Use a unique msgid, msgid_plural "
            "combination or add a msgctxt to differentiate",
        )

        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgctxt "t1"
                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "1"
                msgstr[1] "2"

                msgctxt "t1"
                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "3"
                msgstr[1] "4"
            """,
            "A duplicate (msgid, msgid_plural) combination was "
            "detected (p1, p2). Use a unique msgid, msgid_plural "
            "combination or a unique msgctxt to differentiate "
            "(the existing msgctxt 't1' is a duplicate one)",
        )

    def test_incomplete_plurals(self):
        self._test_parse_error(
            """
                msgid ""
                msgstr ""

                msgid "p1"
                msgid_plural "p2"
                msgstr[0] "Not a plural"
                msgstr[1] ""
            """,
            "Incomplete plural forms found on the entry with msgid 'p1' and "
            "msgid_plural 'p2'",
        )

    def test_invalid_po_raised_as_parseerror(self):
        source = "blyargh"
        with self.assertRaises(ParseError):
            self.handler.parse(source)

    def test_pot(self):
        sources = [
            strip_leading_spaces(
                """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr ""

                msgid "two"
                msgstr ""
                """
            ),
            strip_leading_spaces(
                """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr "\\n"

                msgid "two"
                msgstr ""
                """
            ),
            strip_leading_spaces(
                """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr ""

                msgid "two"
                msgstr "\\n"
                """
            ),
        ]
        templates = []
        for source in sources:
            template, stringset = self.handler.parse(source, is_source=True)
            templates.append(template)
            self.assertEqual(len(stringset), 2)
            self.assertEqual(stringset[0].string, "one")
            self.assertEqual(stringset[1].string, "two")
        for t in templates[1:]:
            self.assertEqual(t, templates[0])

        source = strip_leading_spaces(
            """
                msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgid_plural "ones"
                msgstr[0] ""
                msgstr[1] ""

                msgid "two"
                msgstr ""
            """
        )
        template, stringset = self.handler.parse(source, is_source=True)
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].strings, {0: "one", 1: "ones"})
        self.assertEqual(stringset[1].string, "two")

    def test_spaces_treated_like_not_empty(self):
        source = strip_leading_spaces(
            """
            msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr "one"

                msgid "two"
                msgstr "\\n"
            """
        )
        template, stringset = self.handler.parse(source, is_source=True)
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].string, "one")
        self.assertEqual(stringset[1].string, "\n")

        source = strip_leading_spaces(
            """
            msgid ""
                msgstr ""
                "Content-Type: text/plain; charset=UTF-8\n"
                "Content-Transfer-Encoding: 8bit\n"
                "Language: en\n"
                "Plural-Forms: nplurals=2; plural=(n != 1);\n"

                msgid "one"
                msgstr "\\n"

                msgid "two"
                msgstr "two"
            """
        )
        template, stringset = self.handler.parse(source, is_source=True)
        self.assertEqual(len(stringset), 2)
        self.assertEqual(stringset[0].string, "\n")
        self.assertEqual(stringset[1].string, "two")
