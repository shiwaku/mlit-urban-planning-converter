# 都市計画決定GISデータ → PMTiles / GeoParquet パイプライン
#
# 使い方:
#   make setup                 # venv 作成 + 依存インストール
#   make scrape                # ダウンロードページ解析
#   make download              # 全県 GeoJSON 取得（PREF="東京都 京都府" で県指定）
#   make convert               # PMTiles 生成（SPLIT=theme|prefecture）
#   make parquet               # テーマ別 GeoParquet 生成（THEME="youto tokei" で絞り込み）
#   make qml                   # QGIS 用スタイル styles/*.qml 生成
#   make catalog               # manifest / versions.json / CATALOG.md 生成
#   make all                   # scrape→download→convert→parquet→qml→catalog
#   make check-update          # 更新有無の判定（CI用）
#   make clean / clean-dist

PY        ?= python3
VENV      ?= .venv
RUN        = PYTHONPATH=src $(VENV)/bin/$(PY) -m tosiko_pmtiles.cli
SPLIT     ?= theme
MINZOOM   ?= 4
MAXZOOM   ?= 14
PREF      ?=
THEME     ?=
EXTRA     ?=

PREF_ARGS  = $(foreach p,$(PREF),--pref $(p))
THEME_ARGS = $(foreach t,$(THEME),--theme $(t))

.PHONY: setup scrape download convert parquet qml catalog all check-update clean clean-dist

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

parquet:
	$(RUN) parquet $(THEME_ARGS)

qml:
	$(RUN) qml $(THEME_ARGS)

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
