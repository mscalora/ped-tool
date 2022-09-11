import os
import sys
import glob
import random
import shutil
import tempfile
from io import StringIO
from unittest import TestCase
from unittest.mock import patch
from stat import S_IREAD, S_IRGRP, S_IROTH
import ped

tests_path = os.path.dirname(__file__)
data_path = os.path.join(tests_path, 'data')
abcdef_path = os.path.join(data_path, 'abcdef.txt')
abc_def_path = os.path.join(data_path, 'abc_def.txt')
short_path = os.path.join(data_path, 'short.txt')
short_uc_path = os.path.join(data_path, 'short_uc.txt')
long_path = os.path.join(data_path, 'long.txt')


def file_get_contents(path: str):
    with open(path, encoding='utf8') as f:
        return f.read()


class TestPed(TestCase):
    def setUp(self):
        self.ped = ped

    def run_args(self, args: list[str]):
        with patch('sys.stdout', new=StringIO()) as output:
            self.ped.catching_main(args)
            return output.getvalue()

    def run_piped(self, args: list[str], str_input: str, err=False):
        with patch('sys.stdin', new=StringIO(str_input)):
            with patch('sys.stdout', new=StringIO()) as stdout:
                with patch('sys.stderr', new=StringIO()) as stderr:
                    self.ped.catching_main(args)
                    return (stdout.getvalue(), stderr.getvalue()) if err else stdout.getvalue()


short_text = 'this is a test\nof this thing here \nand you might be special.'


class TestOptions(TestPed):

    def test_noop(self):
        out = self.run_args(['-f', abcdef_path])
        self.assertEqual(out, 'abcdef')
        out = self.run_args(['--filepath', abcdef_path])
        self.assertEqual(out, 'abcdef')

    def test_noop_norm(self):
        out = self.run_args(['-f', abcdef_path])
        self.assertEqual(out, 'abcdef')
        out = self.run_args(['-n', '-f', abcdef_path])
        self.assertEqual(out, 'abcdef\n')
        out = self.run_args(['--normalize', '-f', abcdef_path])
        self.assertEqual(out, 'abcdef\n')
        out = self.run_args(['--no-eof', '--normalize', '--filepath', abcdef_path])
        self.assertEqual(out, 'abcdef')

    def test_line_ending(self):
        out = self.run_args(['-n', '-f', abcdef_path, '--line-ending', '\r'])
        self.assertEqual(out, 'abcdef\r')
        out = self.run_args(['-n', '-f', abcdef_path, '--line-ending', ':'])
        self.assertEqual(out, 'abcdef:')

    def test_delimiters(self):
        out = self.run_piped(['S:this:------'], 'this or that, that or this')
        self.assertEqual(out, '------ or that, that or ------')

    def test_normalize(self):
        out = self.run_args(['-f', abcdef_path, '-n'])
        self.assertEqual(out, 'abcdef\n')

    def test_inplace(self):
        with tempfile.TemporaryDirectory('_test') as temp_dir:
            temp_path = os.path.join(temp_dir, 'shorty.txt')
            shutil.copy2(short_path, temp_path)
            out = self.run_args(['-e', '-f', temp_path, 's/[aeiou]/-'])
            text = file_get_contents(temp_path)
            self.assertEqual(text, 'th-s -s - t-st\n-f th-s th-ng h-r- \n-nd y-- m-ght b- sp-c--l.\n')
            out = self.run_args(['--in-place', '-f', temp_path, 's/[aeiou]/-'])
            text = file_get_contents(temp_path)
            self.assertEqual(text, 'th-s -s - t-st\n-f th-s th-ng h-r- \n-nd y-- m-ght b- sp-c--l.\n')

    def test_ignore_case(self):
        out = self.run_args(['-i', '-f', short_path, 's/[aeIOU]/-'])
        self.assertEqual(out, 'th-s -s - t-st\n-f th-s th-ng h-r- \n-nd y-- m-ght b- sp-c--l.\n')
        out = self.run_args(['--ignore-case', '-f', short_uc_path, 's/[aeiOU]/-'])
        self.assertEqual(out, 'TH-S -S - T-ST\n-F TH-S TH-NG H-R- \n-ND Y-- M-GHT B- SP-C--L.\n')
        out = self.run_args(['--ignore-case', '-f', short_path, 'g/thing|SPECIAL/-'])
        self.assertEqual(out, 'of this thing here \nand you might be special.\n')
        out = self.run_args(['-f', short_uc_path, 'g/thIS', '-i'])
        self.assertEqual(out, 'THIS IS A TEST\nOF THIS THING HERE \n')

    def test_fixed(self):
        out = self.run_piped(['--fixed', 'S/+++++/-----'], '#####&&&&&+++++((((()))))')
        self.assertEqual(out, '#####&&&&&-----((((()))))')
        out = self.run_piped(['-F', 'S/+++++/-----'], '#####&&&&&+++++((((()))))')
        self.assertEqual(out, '#####&&&&&-----((((()))))')
        out = self.run_piped(['S/#+/-----'], '#####&&&&&+++++((((()))))')
        self.assertEqual(out, '-----&&&&&+++++((((()))))')

    def test_multiline(self):
        out = self.run_args(['-f', short_path, r'S/^/===> '])
        self.assertEqual(out, '===> this is a test\nof this thing here \nand you might be special.')
        out = self.run_args(['-m', '-f', short_path, r'S/^\W*/===> '])
        self.assertEqual(out, '===> this is a test\n===> of this thing here \n===> and you might be special.')
        out = self.run_args(['--multiline', '-f', short_path, r'S/^\W*/===> '])
        self.assertEqual(out, '===> this is a test\n===> of this thing here \n===> and you might be special.')

    def test_dotall(self):
        out = self.run_piped(['S/##.*&&/-----'], '#####\n&&&&&\n*****\n((((()))))')
        self.assertEqual(out, '#####\n&&&&&\n*****\n((((()))))')
        out = self.run_piped(['--dotall', 'S/##.*&&/-----'], '#####\n&&&&&\n*****\n((((()))))')
        self.assertEqual(out, '-----\n*****\n((((()))))')
        out = self.run_piped(['-d', 'S/##.*&&/-----'], '#####\n&&&&&\n*****\n((((()))))')
        self.assertEqual(out, '-----\n*****\n((((()))))')

    def test_ascii(self):
        out = self.run_piped(['S/\s/-'],
                             ' \t\n\r\xA0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a')
        self.assertEqual(out, '----------------')
        out = self.run_piped(['--ascii', 'S/\s/-'],
                             ' \t\n\r\xA0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a')
        self.assertEqual(out, '----\xA0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a')
        out = self.run_piped(['-a', 'S/\s/-'],
                             ' \t\n\r\xA0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a')
        self.assertEqual(out, '----\xA0\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a')

    def test_backup(self):
        for opt in ['-b', '--backup-path']:
            num = random.randint(1000000, 9999999)
            temp_inplace = f'/tmp/temp_inplace_test_{num}.txt'
            temp_path = f'/tmp/backup_test_{num}'
            shutil.copy2(short_path, temp_inplace)
            before = file_get_contents(temp_inplace)
            self.assertEqual(short_text, before)
            self.run_args(['-e', opt, temp_path, '-f', temp_inplace, 's/[aeiou]/-'])
            file_list = glob.glob(os.path.join(temp_path, '*'))
            self.assertEqual(len(file_list), 1)
            backup = file_get_contents(file_list[0])
            self.assertEqual(before, backup)
            after = file_get_contents(temp_inplace)
            self.assertNotEqual(before, after)

    def test_no_eof(self):
        out = self.run_piped(['s/[aeiou]/-'], 'abcdefghi\njklmnopqrs\ntuvwxyz')
        self.assertEqual(out, '-bcd-fgh-\njklmn-pqrs\nt-vwxyz\n')
        out = self.run_piped(['--no-eof', 's/[aeiou]/-'], 'abcdefghi\njklmnopqrs\ntuvwxyz')
        self.assertEqual(out, '-bcd-fgh-\njklmn-pqrs\nt-vwxyz')
        out = self.run_piped(['-Z', 's/[aeiou]/-'], 'abcdefghi\njklmnopqrs\ntuvwxyz')
        self.assertEqual(out, '-bcd-fgh-\njklmn-pqrs\nt-vwxyz')

    def test_no_eof2(self):
        out = self.run_piped(['s/[aeiou]/-'], 'abcdefghijklmnopqrstuvwxyz\nabcdefghijklmnopqrstuvwxyz')
        self.assertEqual(out, '-bcd-fgh-jklmn-pqrst-vwxyz\n-bcd-fgh-jklmn-pqrst-vwxyz\n')
        out = self.run_piped(['-M', '3', 's/[aeiou]/-'], 'abcdefghijklmnopqrstuvwxyz\nabcdefghijklmnopqrstuvwxyz')
        self.assertEqual(out, '-bcd-fgh-jklmnopqrstuvwxyz\nabcdefghijklmnopqrstuvwxyz\n')
        out = self.run_piped(['--max-sub', '8', 's/[aeiou]/-'],
                             'abcdefghijklmnopqrstuvwxyz\nabcdefghijklmnopqrstuvwxyz')
        self.assertEqual(out, '-bcd-fgh-jklmn-pqrst-vwxyz\n-bcd-fgh-jklmnopqrstuvwxyz\n')
        out = self.run_piped(['-M', '6', '-L', '4', 's/[aeiou]/-'],
                             'abcdefghijklmnopqrstuvwxyz\nabcdefghijklmnopqrstuvwxyz')
        self.assertEqual(out, '-bcd-fgh-jklmn-pqrstuvwxyz\n-bcd-fghijklmnopqrstuvwxyz\n')
        out = self.run_piped(['--line-max-sub', '2', 's/[aeiou]/-'],
                             'abcdefghijklmnopqrstuvwxyz\nabcdefghijklmnopqrstuvwxyz')
        self.assertEqual(out, '-bcd-fghijklmnopqrstuvwxyz\n-bcd-fghijklmnopqrstuvwxyz\n')

    def test_help(self):
        with self.assertRaises(SystemExit) as ex1:
            self.run_piped(['--help'], 'test', err=True)
        with self.assertRaises(SystemExit) as ex2:
            self.run_piped(['-h'], 'test', err=True)


class TestCommands(TestPed):

    def test_line_sub(self):
        out = self.run_args(['-f', abcdef_path, 's/c/C/'])
        self.assertEqual(out, 'abCdef\n')
        out = self.run_args(['-f', abc_def_path, 's/^../x/'])
        self.assertEqual(out, 'xc\nxf\n')
        out = self.run_args(['-f', abc_def_path, 's/[ace]/@@@/'])
        self.assertEqual(out, '@@@b@@@\nd@@@f\n')
        out = self.run_args(['-f', short_path, 's/this|here/----/'])
        self.assertEqual(out, '---- is a test\nof ---- thing ---- \nand you might be special.\n')
        out = self.run_args(['-f', short_path, '-L', '1', 's/this|here/----/'])
        self.assertEqual(out, '---- is a test\nof ---- thing here \nand you might be special.\n')
        out = self.run_args(['-f', short_path, 's/[aeiou]/#/'])
        self.assertEqual(out, 'th#s #s # t#st\n#f th#s th#ng h#r# \n#nd y## m#ght b# sp#c##l.\n')
        out = self.run_args(['-f', short_path, '-L', '3', '-M', '8', 's/[aeiou]/•'])
        self.assertEqual(out, 'th•s •s • test\n•f th•s th•ng here \n•nd y•u might be special.\n')

    def test_file_sub(self):
        out = self.run_args(['-f', abcdef_path, 'S/c/C/'])
        self.assertEqual(out, 'abCdef')
        out = self.run_args(['-n', '-f', abcdef_path, 'S/c/C/'])
        self.assertEqual(out, 'abCdef\n')
        out = self.run_args(['-n', '-f', abc_def_path, 'S/c/C/'])
        self.assertEqual(out, 'abC\ndef\n')
        out = self.run_args(['-n', '-f', abc_def_path, 'S/c\nd/C\nD/'])
        self.assertEqual(out, 'abC\nDef\n')
        out = self.run_args(['-nm', '-f', abc_def_path, 'S/.$/X/'])
        self.assertEqual(out, 'abX\ndeX\n')

    def test_fixed_sub(self):
        out = self.run_args(['-f', short_path, 'f/./!/'])
        self.assertEqual(out, 'this is a test\nof this thing here \nand you might be special!\n')

    def test_grep(self):
        out = self.run_args(['-f', short_path, 'g/thing'])
        self.assertEqual(out, 'of this thing here \n')
        out = self.run_args(['-f', short_path, r'g/\b\w{5}\b/'])
        self.assertEqual(out, 'of this thing here \nand you might be special.\n')
        out = self.run_args(['-f', short_path, r'g/\b\w{5}\b/'])
        self.assertEqual(out, 'of this thing here \nand you might be special.\n')
        e = ('Python is an interpreted, interactive, object-oriented programming language. It \n' +
             'applications that need a programmable interface. Finally, Python is portable: it \n')
        out = self.run_args(['-f', long_path, '-im', r'g/it $'])
        self.assertEqual(out, e)

    def test_line_grep(self):
        out = self.run_args(['-f', short_path, 'G/.*special.*'])
        self.assertEqual(out, 'and you might be special.\n')
        out = self.run_args(['-f', short_path, r'G/of.*here\s?'])
        self.assertEqual(out, 'of this thing here \n')

    def test_exclude(self):
        out = self.run_args(['-f', short_path, r'x/this'])
        self.assertEqual(out, 'and you might be special.\n')
        out = self.run_args(['-f', long_path, '-dm', r'x/\b[A-Z]'])
        text = ('incorporates modules, exceptions, dynamic typing, very high level dynamic data \n' +
                'object-oriented programming, such as procedural and functional programming. \n' +
                'many system calls and libraries, as well as to various window systems, and is \n')
        self.assertEqual(out, text)

    def test_line_exclude(self):
        out = self.run_args(['-f', short_path, '-dm', r'X/[a-eg-z .]*/'])
        self.assertEqual(out, 'of this thing here \n')

    def test_line_only(self):
        out = self.run_args(['-f', short_path, '-dm', r'o/\b\w{7}\b'])
        self.assertEqual(out, 'special\n')
        out = self.run_args(['-f', long_path, '-dm', r'o/\b\w+[ .]*$', r'S/\s+/ ', r'S/ $|\./'])
        self.assertEqual(out, 'It data beyond programming to is for it Windows')

    def test_file_only(self):
        out = self.run_args(['-f', short_path, '-dm', r'O/\b\w{7}\b'])
        self.assertEqual(out, 'special')
        out = self.run_args(['-f', short_path, '--dotall', r'O/\b\w{5}\b.*\b\w{5}\b/'])
        self.assertEqual(out, 'thing here \nand you might')
        out = self.run_args(['-f', long_path, '-dm', r'O/\b\w{7}\b'])
        self.assertEqual(out, 'modulesdynamicdynamicclassesvarioussystemsFinallyWindows')

    def test_line_remove(self):
        out = self.run_args(['-f', short_path, '-dm', r'r/\b\w{2,5}\b( |$|.)'])
        self.assertEqual(out, 'a \n\nspecial.\n')

    def test_file_remove(self):
        out = self.run_args(['-f', short_path, '-dm', r'R/\b\w{2,5}\b( |\n|$|\.)+/'])
        self.assertEqual(out, 'a special.')

    def test_line_upper(self):
        out = self.run_args(['-f', short_path, r'u/\b\w{3,4}\b'])
        self.assertEqual(out, 'THIS is a TEST\nof THIS thing HERE \nAND YOU might be special.\n')

    def test_file_upper(self):
        out = self.run_args(['-f', short_path, '-dm', r'U/\b\w{4}\s?\n\w{2,4}\b'])
        self.assertEqual(out, 'this is a TEST\nOF this thing HERE \nAND you might be special.')

    def test_line_lower(self):
        out = self.run_args(['-f', short_uc_path, r'l/\b\w{3,4}\b'])
        self.assertEqual(out, 'this IS A test\nOF this THING here \nand you MIGHT BE SPECIAL.\n')

    def test_file_lower(self):
        out = self.run_args(['-f', short_uc_path, '-dm', r'L/\b\w{4}\s?\n\w{2,4}\b'])
        self.assertEqual(out, 'THIS IS A test\nof THIS THING here \nand YOU MIGHT BE SPECIAL.')

    def test_line_title(self):
        out = self.run_args(['-f', short_uc_path, r't/\b\w.*\w\b'])
        self.assertEqual(out, 'This Is A Test\nOf This Thing Here \nAnd You Might Be Special.\n')

    def test_file_title(self):
        out = self.run_args(['-f', short_path, '-dm', r'T/\b\w{4}\s?\n\w{2,4}\b'])
        self.assertEqual(out, 'this is a Test\nOf this thing Here \nAnd you might be special.')
        out = self.run_args(['-f', short_uc_path, '-dm', r'T/\b\w{4}\s?\n\w{2,4}\b'])
        self.assertEqual(out, 'THIS IS A Test\nOf THIS THING Here \nAnd YOU MIGHT BE SPECIAL.')

    def test_line_cap(self):
        out = self.run_args(['-f', short_uc_path, r'c/\b\w.*\w\b'])
        self.assertEqual(out, 'This is a test\nOf this thing here \nAnd you might be special.\n')

    def test_file_cap(self):
        out = self.run_args(['-f', short_path, '-dm', r'C/\b\w{4}\s?\n\w{2,4}\b'])
        self.assertEqual(out, 'this is a Test\nof this thing Here \nand you might be special.')
        out = self.run_args(['-f', short_uc_path, '-dm', r'C/\b\w{4}\s?\n\w{2,4}\b'])
        self.assertEqual(out, 'THIS IS A Test\nof THIS THING Here \nand YOU MIGHT BE SPECIAL.')

    def test_append_line(self):
        out = self.run_args(['-f', abcdef_path, r'a/123456'])
        self.assertEqual(out, 'abcdef\n123456\n')
        out = self.run_args(['-f', short_path, 'a/oh yea?\nyea!'])
        self.assertEqual(out, 'this is a test\nof this thing here \nand you might be special.\noh yea?\nyea!\n')

    def test_append_char(self):
        out = self.run_args(['-f', abcdef_path, r'A/123456'])
        self.assertEqual(out, 'abcdef123456')
        out = self.run_args(['-f', short_path, 'A/oh yea?\nyea!'])
        self.assertEqual(out, 'this is a test\nof this thing here \nand you might be special.oh yea?\nyea!')
        out = self.run_args(['-n', '-f', short_path, 'A/oh yea?\nyea!'])
        self.assertEqual(out, 'this is a test\nof this thing here \nand you might be special.\noh yea?\nyea!')

    def test_prepend_line(self):
        out = self.run_args(['-f', abcdef_path, 'p/123456'])
        self.assertEqual(out, '123456\nabcdef\n')
        out = self.run_args(['-f', short_path, 'p/oh yea?\nyea!'])
        self.assertEqual(out, 'oh yea?\nyea!\nthis is a test\nof this thing here \nand you might be special.\n')

    def test_prepend_char(self):
        out = self.run_args(['-f', abcdef_path, 'P/123456'])
        self.assertEqual(out, '123456abcdef')
        out = self.run_args(['-f', short_path, 'P/oh yea?\nyea!'])
        self.assertEqual(out, 'oh yea?\nyea!this is a test\nof this thing here \nand you might be special.')
        out = self.run_args(['-n', '-f', short_path, 'P/oh yea?\nyea!'])
        self.assertEqual(out, 'oh yea?\nyea!this is a test\nof this thing here \nand you might be special.\n')

    def test_insert_line(self):
        out = self.run_args(['-f', abcdef_path, 'i/0/123456'])
        self.assertEqual(out, '123456\nabcdef\n')
        out = self.run_args(['-f', abcdef_path, 'i/1/123456'])
        self.assertEqual(out, 'abcdef\n123456\n')
        out = self.run_args(['-f', abcdef_path, 'i/-5/123456'])
        self.assertEqual(out, '123456\nabcdef\n')
        out = self.run_args(['-f', abcdef_path, 'i/5/123456'])
        self.assertEqual(out, 'abcdef\n123456\n')
        out = self.run_args(['-f', short_path, 'i/2/123456'])
        self.assertEqual(out, 'this is a test\nof this thing here \n123456\nand you might be special.\n')
        out = self.run_args(['-f', short_path, 'i/-2/123456'])
        self.assertEqual(out, 'this is a test\n123456\nof this thing here \nand you might be special.\n')

    def test_insert_char(self):
        out = self.run_args(['-f', abcdef_path, 'I/0/123456'])
        self.assertEqual(out, '123456abcdef')
        out = self.run_args(['-f', abcdef_path, 'I/6/123456'])
        self.assertEqual(out, 'abcdef123456')
        out = self.run_args(['-f', abcdef_path, 'I/-50/123456'])
        self.assertEqual(out, '123456abcdef')
        out = self.run_args(['-f', abcdef_path, 'I/10000/123456'])
        self.assertEqual(out, 'abcdef123456')
        out = self.run_args(['-f', short_path, 'I/6/123456'])
        self.assertEqual(out, 'this i123456s a test\nof this thing here \nand you might be special.')
        out = self.run_args(['-f', short_path, 'I/-10/123456'])
        self.assertEqual(out, 'this is a test\nof this thing here \nand you might b123456e special.')

    def test_replace_lines(self):
        out = self.run_args(['-f', abcdef_path, 'y/0/0/123456'])
        self.assertEqual(out, '123456\nabcdef\n')
        out = self.run_args(['-f', abcdef_path, 'y/1/0/123456'])
        self.assertEqual(out, 'abcdef\n123456\n')
        out = self.run_args(['-f', short_path, 'y/2/0/123456'])
        self.assertEqual(out, 'this is a test\nof this thing here \n123456\nand you might be special.\n')
        out = self.run_args(['-f', short_path, 'y/1/1/123456'])
        self.assertEqual(out, 'this is a test\n123456\nand you might be special.\n')
        out = self.run_args(['-f', short_path, 'y/1/2/123456'])
        self.assertEqual(out, 'this is a test\n123456\n')
        out = self.run_args(['-f', short_path, 'y/0/2/123456'])
        self.assertEqual(out, '123456\nand you might be special.\n')

    def test_replace_chars(self):
        out = self.run_args(['-f', abcdef_path, 'Y/0/0/123456'])
        self.assertEqual(out, '123456abcdef')
        out = self.run_args(['-f', abcdef_path, 'Y/6/0/123456'])
        self.assertEqual(out, 'abcdef123456')
        out = self.run_args(['-f', abcdef_path, 'Y/-50/0/123456'])
        self.assertEqual(out, '123456abcdef')
        out = self.run_args(['-f', abcdef_path, 'Y/10000/0/123456'])
        self.assertEqual(out, 'abcdef123456')
        out = self.run_args(['-f', abcdef_path, 'Y/2/2/123456'])
        self.assertEqual(out, 'ab123456ef')
        out = self.run_args(['-f', short_path, 'Y/5/4/123456'])
        self.assertEqual(out, 'this 123456 test\nof this thing here \nand you might be special.')
        out = self.run_args(['-f', short_path, 'Y/-11/2/123456'])
        self.assertEqual(out, 'this is a test\nof this thing here \nand you might 123456 special.')

    def test_delete_lines(self):
        out = self.run_args(['-f', abcdef_path, 'd/0/0'])
        self.assertEqual(out, 'abcdef\n')
        out = self.run_args(['-f', short_path, 'd/2/4/'])
        self.assertEqual(out, 'this is a test\nof this thing here \n')
        out = self.run_args(['-f', short_path, 'd/0/2/123456'])
        self.assertEqual(out, 'and you might be special.\n')

    def test_delete_chars(self):
        out = self.run_args(['-f', abcdef_path, 'D/2/2'])
        self.assertEqual(out, 'abef')
        out = self.run_args(['-f', abcdef_path, 'D/3/6'])
        self.assertEqual(out, 'abc')
        out = self.run_args(['-f', abcdef_path, 'D/0/4'])
        self.assertEqual(out, 'ef')
        out = self.run_args(['-f', short_path, 'D/5/44'])
        self.assertEqual(out, 'this be special.')
        out = self.run_args(['-f', short_path, 'D/-32/200'])
        self.assertEqual(out, 'this is a test\nof this thing')


class TestMultipleCommands(TestPed):

    def test_ssss(self):
        out = self.run_args(['-f', abcdef_path, 's/c/abcdef', 's/c/abcdef', 's/c/abcdef', 's/c/abcdef', 's/c/abcdef'])
        self.assertEqual(out, 'ababababababcdefdefdefdefdefdef\n')

    def test_ais(self):
        out = self.run_piped(['a/top\nbottom', 'i/1/middle', 's/^/> '], '')
        self.assertEqual(out, '> top\n> middle\n> bottom\n')
        out = self.run_piped(['a/top\nbottom', 'i/1/mid\ndle', 's/^/> '], '')
        self.assertEqual(out, '> top\n> mid\n> dle\n> bottom\n')

    def test_aiss(self):
        out = self.run_piped(['a/top\nbottom', 'i/1/middle', 's/^m.*/two\nlines/', 's/^/> '], '')
        self.assertEqual(out, '> top\n> two\n> lines\n> bottom\n')
        out = self.run_piped(['a/top\nbottom', 'i/1/mid\ndle', 's/^m.*/two\nlines/', 's/^/> '], '')
        self.assertEqual(out, '> top\n> two\n> lines\n> dle\n> bottom\n')

    def test_ss(self):
        out = self.run_args(['-f', short_path, 's/thing/\n', 's/^/> '])
        self.assertEqual(out, '> this is a test\n> of this \n>  here \n> and you might be special.\n')

    def test_as(self):
        out = self.run_piped(['a/a\nb\nc', 's/^/> /'], '')
        self.assertEqual(out, '> a\n> b\n> c\n')

    def test_ps(self):
        out = self.run_piped(['p/a\nb\nc', 's/^/> /'], '')
        self.assertEqual(out, '> a\n> b\n> c\n')

    def test_is(self):
        out = self.run_piped(['i/1/xx\nyy\nzz', 's/^/> /'], 'a\nb\nc')
        self.assertEqual(out, '> a\n> xx\n> yy\n> zz\n> b\n> c\n')

    def test_ys(self):
        out = self.run_piped(['y/1/1/xx\nyy\nzz', 's/^/> /'], 'a\nb\nc')
        self.assertEqual(out, '> a\n> xx\n> yy\n> zz\n> c\n')


class TestErrors(TestPed):

    def test_unknown_command(self):
        with self.assertRaises(ped.PedError) as ex:
            out = self.run_piped(['🌀/?/'], 'test')
        self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_UNKNOWN_COMMAND_ERROR)

    def test_backup_dir(self):
        with tempfile.TemporaryDirectory('_backup_test') as temp_dir:
            temp_path = os.path.join(temp_dir, 'shorty.txt')
            shutil.copy2(short_path, temp_path)
            with self.assertRaises(ped.PedError) as ex:
                # using temp file as backup dir path error should trigger IO error
                out = self.run_args(['--in-place', '--backup-path', temp_path, '-f', temp_path, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_IO_ERROR)

    def test_re_error(self):
        with self.assertRaises(ped.PedError) as ex:
            out = self.run_piped(['s/?/'], 'test')
        self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_RE_ERROR)

    def test_io_error(self):
        with self.assertRaises(ped.PedError) as ex:
            out = self.run_piped(['-f', '/home', 's/./-'], '')
        self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_IO_ERROR)

    def test_permission_error(self):
        with self.assertRaises(ped.PedError) as ex:
            out = self.run_piped(['-f', '/home', 's/./-'], '')
        self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_IO_ERROR)

    def test_ro_io_error(self):
        """test failure with write permissions on target inplace edit file"""
        with tempfile.TemporaryDirectory('ro_test') as temp_dir:
            temp_path = os.path.join(temp_dir, 'ro_shorty.txt')
            shutil.copy2(short_path, temp_path)
            os.chmod(temp_path, S_IREAD|S_IRGRP|S_IROTH)
            with self.assertRaises(ped.PedError) as ex:
                out = self.run_args(['-e', '-f', temp_path, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_IO_ERROR)

    def test_ro_bu_io_error(self):
        """test failure with write permissions on backup dir"""
        with tempfile.TemporaryDirectory('ro_test') as temp_dir:
            temp_path = os.path.join(temp_dir, 'ro_shorty.txt')
            shutil.copy2(short_path, temp_path)
            temp_bu_path = os.path.join(temp_dir, 'backups')
            os.mkdir(temp_bu_path)
            os.chmod(temp_bu_path, S_IREAD|S_IRGRP|S_IROTH)
            with self.assertRaises(ped.PedError) as ex:
                out = self.run_args(['-e', '--backup-path', temp_bu_path,'-f', temp_path, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_IO_ERROR)

    def test_fnf(self):
        with tempfile.TemporaryDirectory('ro_test') as temp_dir:
            num = random.randint(10000000, 99999999)
            temp_fnf = os.path.join(temp_dir, f'temp_fnf_test_{num}.txt')
            with self.assertRaises(ped.PedError) as ex:
                self.run_args(['-f', temp_fnf, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_IO_ERROR)

    def test_other_1(self):
        with patch('builtins.open', error_open_msg):
            with self.assertRaises(ped.PedError) as ex:
                self.run_args(['-f', short_path, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_OTHER_ERROR)

    def test_other_2(self):
        with patch('builtins.open', error_open_message):
            with self.assertRaises(ped.PedError) as ex:
                self.run_args(['-f', short_path, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_OTHER_ERROR)

    def test_other_3(self):
        with patch('builtins.open', error_open_strerror):
            with self.assertRaises(ped.PedError) as ex:
                self.run_args(['-f', short_path, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_OTHER_ERROR)

    def test_other_4(self):
        with patch('builtins.open', error_open_unknown):
            with self.assertRaises(ped.PedError) as ex:
                self.run_args(['-f', short_path, 's/[aeiou]/-'])
            self.assertEqual(ex.exception.type, ped.PedErrorTypes.PED_OTHER_ERROR)


def error_open_msg(*_arg, **_kwargs):
    class ErrMsg(Exception):
        def __init__(self, message):
            self.msg = message
    raise ErrMsg('msg message')


def error_open_message(*_arg, **_kwargs):
    class ErrMsg(Exception):
        def __init__(self, message):
            self.message = message
    raise ErrMsg('message message')


def error_open_strerror(*_arg, **_kwargs):
    class ErrMsg(Exception):
        def __init__(self, message):
            self.strerror = message
    raise ErrMsg('strerror message')


def error_open_unknown(*_arg, **_kwargs):
    class ErrMsg(Exception):
        def __init__(self, message):
            self.unknown = message
    raise ErrMsg('unknown message')
