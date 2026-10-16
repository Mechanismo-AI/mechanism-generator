#!/usr/bin/env python3
"""One-command corpus-digest handoff to the clerk node.

Builds the same digest prompt as generate_corpus_digest_prompt.py on this
machine, then delivers it to the clerk worker's queue on another machine
(default ssh alias "megabox"). Idempotent: if the clerk node already holds
any prompt with this --name prefix in pending/, processing/, done/, or
failed/, the command says so and sends nothing. Fail-closed: ssh/scp
problems abort loudly, and the prompt is left in this clone's
queue/pending/ so nothing is lost.

    python jobs/local-llm-queue/send_digest.py runs/sync-corpus-03 --name corpus03

The answer will appear as <remote-queue>/done/<prompt-name>.answer.md on
the clerk node. Read it over ssh and review it before anything enters the
record: the clerk's numbers are quotes, never computations.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from generate_corpus_digest_prompt import build_prompt, prompt_tag  # noqa: E402

DEFAULT_HOST = "megabox"
DEFAULT_QUEUE = "~/mechanism-generator/jobs/local-llm-queue/queue"
STATES = ("pending", "processing", "done", "failed")


def die(msg: str) -> None:
    print(f"send_digest: FAIL-CLOSED: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run_remote(host: str, command: str, timeout: float = 30.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["ssh", host, commX]Ø\\WÛÝ]]UYK^UYK[Y[Ý]][Y[Ý]
B^Ù\ÝXØÙ\ÜË[Y[Ý]^\YYJÜÚÈÚÜÝ\H[YYÝ]ÛØÛÛ[X[HB^Ù\[SÝÝ[\ÜYJÜÚ\ÈÝ[Ý[YÛ\ÈXXÚ[H8 %[Ý[Ü[ÜÚXÛY[\ÝBYXZ[
HO[\Ù\H\Ü\ÙK\Ý[Y[\Ù\\ØÜ\[ÛW×ÙØ××ÊB\Ù\YØ\Ý[Y[
ÛÜ\×Ù\\OT][H\XÝÜHÛÛZ[[ÈÝ[[X\KÛÛB\Ù\YØ\Ý[Y[
K[[YHY][SÛK[HÛ\[H\Ù[[YH
Y][HÛÜ\È\[YJHB\Ù\YØ\Ý[Y[
KZÜÝY][QQUSÒÔÕ[YÜÚ[X\ÈÙHÛ\ÈÙH
Y][ÑQUSÒÔÕJHB\Ù\YØ\Ý[Y[
K\[[ÝK\]Y]YHY][QQUSÔUQUQK[Y]Y]YH\ÛHÛ\ÈÙH
Y][ÑQUSÔUQUQ_JHB\ÜÈH\Ù\\ÙWØ\ÜÊ
B[YHH\ÜË[YHÜ\ÜËÛÜ\×Ù\[YBÛÜ\ÈH\ÜËÛÜ\×Ù\\ÛÛJ
BNÛ\HZ[ÜÛ\
ÛÜ\ÊBYÈHÛ\ÝYÊÛÜ\ÊB^Ù\
[SÝÝ[\Ü[YQ\ÜH\ÈNYJÝJJB[YHHÛ[Y_K^ÝYßKYÈKXXÚHÛ\ÈÙH[Ø[ÛXØ[^H]È]Y]YH]
^[ÈK\ÈH[Ü[[ÝJ\ÜËÜÝXÚÈØ\ÜË[[ÝWÜ]Y]Y_HB[\ÈHÛÝ\

HÜ[\ËÝÝ]Ü][\Ê
HYÝ\

WBY\Ë]\ÛÙHOHÜ[[\ÊHOHN]Z[H
\ËÝ\Ü\ËÝÝ]ÜÈÝ]]KÝ\

BYJØ[ÝXXÚÛ\ÈÙHØ\ÜËÜÝ\NÙ]Z[HB]Y]YHH[\ÖÌBØHH[Ü[[ÝJ\ÜËÜÝ\ÝYÜÚ^][ÝJ]Y]YH
È	ËÜ[[ÉÊ_H	XÚÈÚÈBYØK]\ÛÙHOHÜØKÝÝ]Ý\

HOHÚÈ]Z[H
ØKÝ\ÜØKÝÝ]ÜÈÝ]]KÝ\

BYJÈ]Y]YH]Ü]Y]Y_HÛØ\ÜËÜÝ\H8 %\ÈHÛ\ÈÛÜÙ\Ù]\\OÈ
Ù]Z[JHBÈY[\Ý[ÞNÚÚ\YHÛ\ÈÙH[XYHÛÝÜÈ\È[YK]\HÚ^][ÝJ[YH
ÈJB[ØÛYH
[
ÈÚ[Ú^][ÝJÜ]Y]Y_KÞÜÝ]_HHÜÝ]H[ÕUTÊB
È[X^\H[[YHÜ]\H\[\]Z]Ù]Û[
BÙY[H[Ü[[ÝJ\ÜËÜÝ[ØÛY
BYÙY[]\ÛÙHOH[ÙY[ÝÝ]Ý\

N[
[XYHÛÝÛÈHÛ\ÎÜÙY[ÝÝ]Ý\

_HB[
Ý[ÈÙ[[]H]\HY[ÝHX[HØ[HKYYÙ\ÝB]\ÈË[]\ÈHÛ\ÉÜÈ[[ËÈ[\YH\][Ú][\[K[YY[\Ü\Q[JÈÝY^HY[]OQ[ÙK[ÛÙ[ÏH]NH\ÈÜ]JÛ\
B\Ü]H]
[YJBNØÜHÝXØÙ\ÜË[ÈØÜ\HÝ\Ü]
KØ\ÜËÜÝNÜ]Y]Y_KÜ[[ËÞÙ[Y_HKØ\\WÛÝ]]UYK^UYK[Y[Ý]M
B^Ù\
ÝXØÙ\ÜË[Y[Ý]^\Y[SÝÝ[\ÜH\ÈNØÜHÝXØÙ\ÜËÛÛ\]YØÙ\ÜÊ×KLËÝ\JJK×Û[YW×ßNÙ_HBYØÜ]\ÛÙHOH[XÚÈHTHÈ]Y]YHÈ[[È[XÚËZÙ\\[ÏUYK^\ÝÛÚÏUYJBØØ[ØÛÜHH[XÚÈÈ[YBØØ[ØÛÜKÜ]WÝ^
Û\[ÛÙ[ÏH]NB\Ü][[ÊZ\ÜÚ[×ÛÚÏUYJBYJØÜÈØ\ÜËÜÝ\HZ[Y
ÊØÜÝ\Ü	ÉÊKÝ\

_JNÈÛ\\Ù\YØØ[H]ÛØØ[ØÛÜ_H8 %[Ù\]H[Ü]K
B\Ü][[ÊZ\ÜÚ[×ÛÚÏUYJBÚXÚÈH[Ü[[ÝJ\ÜËÜÝ\ÝYÜÚ^][ÝJ]Y]YH
È	ËÜ[[ËÉÈ
È[YJ_H	XÚÈÚÈBYÚXÚË]\ÛÙHOHÜÚXÚËÝÝ]Ý\

HOHÚÈYJØÜ\ÜYÝXØÙ\ÜÈ]Ù[Y_H\ÈÝ[Ü]Y]Y_KÜ[[ËÈÛØ\ÜËÜÝ\H8 %ÚXÚÈH[YÜH\[[ÈB[
[]\YØ\ÜËÜÝNÜ]Y]Y_KÜ[[ËÞÙ[Y_HB[
Û\Ú^NÛ[Û\
_HÚ\ÈB[
H[ÝÙ\Ú[\X\]Ø\ÜËÜÝNÜ]Y]Y_KÙÛKÞÙ[Y_K[ÝÙ\YB]\Y×Û[YW×ÈOH×ÛXZ[×ÈZ\ÙHÞ\Ý[Q^]
XZ[
JB