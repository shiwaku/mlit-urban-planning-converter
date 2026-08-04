<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!-- 居住調整地域（kyojyuchosei）: 国土交通省 都市局『都市計画決定GISデータ』用のスタイル。
     https://github.com/shiwaku/mlit-urban-planning-converter が data/styles.json から生成。
     配色は全国都市計画GISビューア（https://toshikeikaku-info.jp/）を参考にしている。 -->
<qgis version="3.34.0" styleCategories="Symbology|Fields">
  <renderer-v2 type="singleSymbol" forceraster="0" symbollevels="0" enableorderby="0" referencescale="-1">
    <symbols>
    <symbol name="0" type="fill" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">
      <layer class="SimpleFill" enabled="1" locked="0" pass="0">
        <Option type="Map">
          <Option name="color" type="QString" value="0,150,0,128"/>
          <Option name="outline_color" type="QString" value="0,100,0,255"/>
          <Option name="outline_style" type="QString" value="solid"/>
          <Option name="outline_width" type="QString" value="0.2"/>
          <Option name="outline_width_unit" type="QString" value="MM"/>
          <Option name="style" type="QString" value="solid"/>
          <Option name="joinstyle" type="QString" value="bevel"/>
          <Option name="offset" type="QString" value="0,0"/>
          <Option name="offset_unit" type="QString" value="MM"/>
        </Option>
      </layer>
    </symbol>
    </symbols>
  </renderer-v2>
  <layerOpacity>0.5</layerOpacity>
  <aliases>
    <alias field="Pref" index="0" name="都道府県"/>
    <alias field="Citycode" index="1" name="市区町村コード"/>
    <alias field="Cityname" index="2" name="市区町村名"/>
    <alias field="YoutoName" index="3" name="用途地域名"/>
    <alias field="YoutoCode" index="4" name="用途地域コード"/>
    <alias field="FAR" index="5" name="容積率"/>
    <alias field="BCR" index="6" name="建蔽率"/>
    <alias field="AreaType" index="7" name="種類"/>
    <alias field="AreaName" index="8" name="名称"/>
    <alias field="AreaCode" index="9" name="種類コード"/>
    <alias field="TokeiName" index="10" name="都市計画区域名"/>
    <alias field="TokeiType" index="11" name="種類"/>
    <alias field="TokeiCode" index="12" name="種類コード"/>
    <alias field="DistName" index="13" name="名称"/>
    <alias field="DistType" index="14" name="種類"/>
    <alias field="DistCode" index="15" name="種類コード"/>
    <alias field="ParkName" index="16" name="公園名"/>
    <alias field="ParkType" index="17" name="種類"/>
    <alias field="ParkCode" index="18" name="種類コード"/>
    <alias field="DouroType" index="19" name="種類"/>
    <alias field="DouroCode" index="20" name="種類コード"/>
    <alias field="FaciName" index="21" name="施設名"/>
    <alias field="FaciType" index="22" name="種類"/>
    <alias field="FaciCode" index="23" name="種類コード"/>
    <alias field="INDate" index="24" name="当初決定日"/>
    <alias field="FNDate" index="25" name="最終告示日"/>
    <alias field="INNumber" index="26" name="当初告示番号"/>
    <alias field="FNNumber" index="27" name="最終告示番号"/>
    <alias field="ValidType" index="28" name="効力発生日の種類"/>
    <alias field="Custodian" index="29" name="決定者"/>
  </aliases>
  <layerGeometryType>2</layerGeometryType>
</qgis>
