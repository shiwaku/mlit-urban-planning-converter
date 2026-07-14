# 都市計画決定GISデータ → PMTiles パイプライン
#
# 使い方:
#   make setup                 # venv 作成 + 依存インストール
#   make scrape                # ダウンロードページ解析
#   make download              # 全県 GeoJSON 取得（PREF="東京都 京都府" で県指定）
#   make convert               # PMTiles 生成（SPLIT=theme|prefecture）
#   make catalog               # manifest / versions.json / CATALOG.md 生成
#   make all                   # scrape→download→convert→catalog
#   make check-update          # 更新有無の判定（CI用）
#   make clean / clean-dist

PY        ?= python3
VENV      ?= .venv
RUN        = PYTHONPATH=src $(VENV)/bin/$(PY) -m tosiko_pmtiles.cli
SPLIT     ?= theme
MINZOOM   ?= 4
MAXZOOM   ?= 14
PREF      ?=
EXTRA     ?=

PREF_ARGS = $(foreach p,$(PREF),--pref $(p))

.PHONY: setup scrape download convert catalog all check-update clean clean-dist

setup:
	$(PY) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

scrape:
	$(RUN) scrape

download:
	$(RUN) download $(PREF_ARGS)

convert:
	$(RUN) convert --split $(SPLIT) --minzoom $(MINZOOM) --maxzoom $(MAXZOOM) $(if $(EXTRA),--extra "$(EXTRA)",)

catalog:
	$(RUN) catalog --split $(SPLIT)

all:
	$(RUN) all --split $(SPLIT) --minzoom $(MINZOOM) --maxzoom $(MAXZOOM) $(PREF_ARGS) $(if $(EXTRA),--extra "$(EXTRA)",)

check-update:
	$(RUN) check-update

clean-dist:
	rm -rf dist

clean:
	rm -rf raw dist
