import traceback
import adsk
import adsk.core as core
import adsk.fusion as fusion
import pathlib
import re

SUFFIX_MAP = {
    'DXF': '.dxf',
    'STEP': '.stp',
    'IGES': '.igs',
    'SAT': '.sat',
}

class FlatPatternExportFactry():
    def __init__(self) -> None:
        self.app: core.Application = core.Application.get()
        self.flatInfos = self._get_all_flatpattern()


    def exec_export(self, flatPatternIndexList: list, optionList: list, folderPath: str) -> None:
        '''
        エクスポート実行
        '''
        flats = [self.flatInfos[idx] for idx in flatPatternIndexList]

        exportDatas = []
        for info in flats:
            paths = self._get_path(info, optionList, folderPath, exportDatas)
            exportDatas.extend(paths)

        self._exec_export_operation(exportDatas)


    def _exec_export_operation(self, exportDatas: list) -> None:
        '''
        エクスポート実行
        '''
        for exportData in exportDatas:
            path = exportData['path']
            if pathlib.Path(path).suffix == SUFFIX_MAP['DXF']:
                self._export_dxf(exportData)
            else:
                self._export_3d(exportData)


    def _export_dxf(self, exportData: dict) -> None:
        '''
        DXFでエクスポート
        '''
        path = exportData['path']
        flat: fusion.FlatPattern = exportData['flat']

        app: core.Application = self.app
        des: fusion.Design = app.activeProduct
        expMgr: fusion.ExportManager = des.exportManager
        dxfOpt: fusion.DXFFlatPatternExportOptions = expMgr.createDXFFlatPatternExportOptions(
            path,
            flat,
        )
        expMgr.execute(dxfOpt)


    def _export_3d(self, exportData: dict) -> None:
        '''
        3Dでエクスポート
        '''
        # def get_export_options(path: str) -> fusion.ExportOptions:
        #     expMgr: fusion.ExportManager = tmpDes.exportManager

        #     suffix = pathlib.Path(path).suffix
        #     if suffix == SUFFIX_MAP['STEP']:
        #         return expMgr.createSTEPExportOptions(path)
        #     elif suffix == SUFFIX_MAP['IGES']:
        #         return expMgr.createIGESExportOptions(path)
        #     elif suffix == SUFFIX_MAP['SAT']:
        #         return expMgr.createSATExportOptions(path)

        #     return None
        # ****

        flat: fusion.FlatPattern = exportData['flat']
        tmpMgr: fusion.TemporaryBRepManager = fusion.TemporaryBRepManager.get()
        bodyLst = [tmpMgr.copy(b) for b in flat.bodies]
        tmpMgr.exportToFile(bodyLst, exportData['path'])
        # bodyLst = [
        #     tmpMgr.copy(flat.flatBody),
        #     tmpMgr.copy(flat.bendLinesBody),
        #     # tmpMgr.copy(flatPattan.extentLinesBody), #クラッシュしやすい
        # ]

        # app: core.Application = self.app
        # doc: fusion.FusionDocument = app.activeDocument

        # app.documents.add(core.DocumentTypes.FusionDesignDocumentType)
        # tmpDoc: fusion.FusionDocument = app.activeDocument
        # tmpDes: fusion.Design = app.activeProduct

        # doc.activate()

        # tmpDes.designType = fusion.DesignTypes.DirectDesignType
        # tmpRoot: fusion.Component = tmpDes.rootComponent
        # tmpBodies: fusion.BRepBodies = tmpRoot.bRepBodies
        # [tmpBodies.add(b) for b in bodyLst]

        # expMgr: fusion.ExportManager = tmpDes.exportManager
        # exportOpt: fusion.ExportOptions = get_export_options(exportData['path'])
        # expMgr.execute(exportOpt)
        # tmpDoc.close(False)


    def _get_path(self, info: dict, optionList: list, folderPath: str, exportDatas: list) -> list:
        '''
        ユニークなファイルパス取得
        '''
        def is_overlap(path: pathlib.Path) -> bool:
            if path.exists():
                return True
            if str(path) in [x['path'] for x in exportDatas]:
                return True

            return False
        # ********

        paths = []
        stem = self._get_stem_name(info)
        for opt in optionList:
            suffix = SUFFIX_MAP[opt]
            path = pathlib.Path(folderPath) / f'{stem}{suffix}'
            if not is_overlap(path):
                paths.append(
                    {
                        'path':str(path),
                        'flat':info['comp'].flatPattern,
                    }
                )
                continue

            count = 1
            while True:
                path = path.with_stem(f'{stem}_{count}')
                if not is_overlap(path):
                    # return {
                    #     'path':str(path),
                    #     'flat':info['comp'].flatPattern,
                    # }
                    paths.append(
                        {
                            'path':str(path),
                            'flat':info['comp'].flatPattern,
                        }
                    )
                    break
                count += 1
        return paths


    def _get_stem_name(self, info: dict):
        '''
        仮ファイル名取得
        '''
        comp: fusion.Component = info['comp']
        rule: fusion.SheetMetalRule = comp.activeSheetMetalRule
        rule.name
        stem = f'{comp.name}-{rule.name}-{rule.thickness.expression}'

        return re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '_', stem)


    def _get_all_flatpattern(self) -> list:
        '''
        全てのフラットパターン取得
        '''
        des: fusion.Design = self.app.activeProduct
        comps = [c for c in des.allComponents if c.flatPattern]

        infos = [self._create_flat_info(c) for c in comps]
        infos.reverse()
        return infos


    def _create_flat_info(self, comp: fusion.Component) -> dict:
        '''
        フラットパターン情報
        '''
        return {
            'id': comp.entityToken,
            'comp': comp,
            # 'flat': comp.flatPattern,
            # 'rule': comp.activeSheetMetalRule,
            'show': self._is_show_parent_occ(comp)
        }


    def _is_show_parent_occ(self, comp: fusion.Component) -> bool:
        '''
        コンポーネントの親オカレンスが表示されているか？
        '''
        des: fusion.Design = self.app.activeProduct
        root: fusion.Component = des.rootComponent
        if root == comp:
            return True

        occs = root.allOccurrencesByComponent(comp)
        if occs.count < 1:
            return False #ありえない

        occ: fusion.Occurrence = occs[0]

        return occ.isLightBulbOn