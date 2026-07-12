"""Tests for the MyCoin CLI (cli.main called directly with argv lists)."""

from __future__ import annotations

import cli
import wallet


def test_newkey_prints_valid_address(capsys):
    rc = cli.main(["newkey"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert wallet.is_valid_address(out)


def test_subsidy_height_0_is_50(capsys):
    rc = cli.main(["subsidy", "--height", "0"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "50 coins" in out


def test_subsidy_first_halving_is_25(capsys):
    rc = cli.main(["subsidy", "--height", "210000"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "25 coins" in out


def test_mine_two_blocks(capsys):
    rc = cli.main(["mine", "--count", "2"])
    assert rc == 0
    out = capsys.readouterr().out
    # Two mined blocks reach height 2, and the UTXO set holds a nonzero value.
    assert "height=1" in out
    assert "height=2" in out
    assert "total_utxo=0 coins" not in out


def test_info_reports_height_zero(capsys):
    rc = cli.main(["info"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "height:       0" in out


def test_no_subcommand_prints_help_and_returns_zero(capsys):
    rc = cli.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "usage" in out.lower()
