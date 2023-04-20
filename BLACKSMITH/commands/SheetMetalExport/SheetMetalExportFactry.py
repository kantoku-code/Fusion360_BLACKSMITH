from os import remove
import traceback
import adsk
import adsk.core as core
import adsk.fusion as fusion
import pathlib
import re
import os
import pprint
import time

SUFFIX_MAP = {
    'DXF': '.dxf',
    'STEP': '.stp',
    'IGES': '.igs',
    'SAT': '.sat',
}

DEBUG = False

class SheetMetalExportFactry():
    def __init__(self) -> None:
        self.app: core.Application = core.Application.get()
        self.sheetInfos = self._get_sheetMetal_body_infos()


    def export_sheetMetal_flatPattern(
        self, sheetBodyIndexList: list, 
        optionList: list, 
        folderPath: str
    ) -> list[str]:
        '''
        フラットパターンを作成してエクスポート
        '''
        ngLst = []
        self.app.executeTextCommand(u'Transaction.Start sheetmetal_export')
        try:
            for idx in sheetBodyIndexList:
                info: dict = self.sheetInfos[idx]
                try:
                    flat: fusion.FlatPattern = self._create_flatPattern(info['native'])
                    for suffix in optionList:
                        try:
                            path = self._get_path(info, folderPath, SUFFIX_MAP[suffix])
                            dump(path)
                            if suffix == 'DXF':
                                self._export_dxf(path, flat)
                            elif suffix == 'SAT':
                                self._export_sat(path, flat)
                            else:
                                pass
                        except:
                            ngLst.append(path)
                except:
                    ngLst.append(path)
                time.sleep(0.1)
        except:
            pass
        finally:
            self.app.executeTextCommand(u'Transaction.Abort')

        removeLst = [path for path in ngLst if pathlib.Path(path).exists()]
        # pprint.pprint(removeLst)
        for f in removeLst:
            os.remove(f)

        return ngLst


    def _create_flatPattern(self, body: fusion.BRepBody) -> fusion.FlatPattern:
        '''
        フラットパターン作成
        '''
        comp: fusion.Component = body.parentComponent
        flat: fusion.FlatPattern = comp.flatPattern
        try:
            if flat:
                flatProd: fusion.FlatPatternProduct = flat.parentComponent.parentDesign
                flatProd.deleteMe()

            flatFaces = [f for f in body.faces
                if f.geometry.objectType == core.Plane.classType()]

            targetFace: fusion.BRepFace = max(flatFaces, key=lambda f: f.area)

            return comp.createFlatPattern(targetFace)
        except:
            dump(f'_create_flatPattern error: {comp.name}')


    def _create_sheet_info(self, body: fusion.BRepBody) -> dict:
        '''
        シートメタルボディ情報
        '''
        return {
            'id': body.entityToken,
            'native': body,
            'show': False
        }


    def _get_sheetMetal_body_infos(self) -> list:
        '''
        シートメタルボディの取得
        '''
        def get_unique_list(bodyLst: list) -> list:
            body: fusion.BRepBody = None
            dict = {}
            for body in bodyLst:
                if not body.isSheetMetal:
                    continue
                native: fusion.BRepBody = body.nativeObject
                if not native:
                    native = body

                dict.setdefault(
                    native.entityToken,
                    native
                )

            return list(dict.values())
        # *******

        des: fusion.Design = self.app.activeProduct
        root: fusion.Component = des.rootComponent
        showBodyLst = get_unique_list(
            root.findBRepUsingPoint(
                core.Point3D.create(0,0,0),
                fusion.BRepEntityTypes.BRepBodyEntityType,
                100000000,
                True,
            )
        )
        showTokenLst = [b.entityToken for b in showBodyLst]

        allBodyLst = get_unique_list(
            root.findBRepUsingPoint(
                core.Point3D.create(0,0,0),
                fusion.BRepEntityTypes.BRepBodyEntityType,
                100000000,
                False,
            )
        )

        infos = [self._create_sheet_info(b) for b in allBodyLst]
        for info in infos:
            info['show'] = True if info['native'].entityToken in showTokenLst else False

        return infos


    def _export_sat(self, path: str, flat: fusion.FlatPattern) -> None:
        '''
        SATでエクスポート
        '''

        tmpMgr: fusion.TemporaryBRepManager = fusion.TemporaryBRepManager.get()
        bodyLst = [tmpMgr.copy(b) for b in flat.bodies]
        # time.sleep(1)
        res = tmpMgr.exportToFile(bodyLst, path)


    def _export_dxf(self, path: str, flat: fusion.FlatPattern) -> None:
        '''
        DXFでエクスポート
        '''

        app: core.Application = self.app
        des: fusion.Design = app.activeProduct
        expMgr: fusion.ExportManager = des.exportManager
        dxfOpt: fusion.DXFFlatPatternExportOptions = expMgr.createDXFFlatPatternExportOptions(
            path,
            flat,
        )
        res = expMgr.execute(dxfOpt)


    def _get_path(self, info: dict, folderPath: str, suffix: str) -> str:
        '''
        ユニークなファイルパス取得
        '''

        def get_stem_name(info: dict):
            body: fusion.BRepBody= info['native']
            comp: fusion.Component = body.parentComponent
            rule: fusion.SheetMetalRule = comp.activeSheetMetalRule
            stem = f'{body.name}-{comp.name}-{rule.name}-{rule.thickness.expression}'

            return re.sub(r'[\\|/|:|?|.|"|<|>|\|]', '_', stem)

        # ********

        stem = get_stem_name(info)
        # suffix = '.dxf'
        path = pathlib.Path(folderPath) / f'{stem}{suffix}'
        if not path.exists():
            return str(path)

        count = 1
        while True:
            path = path.with_stem(f'{stem}_{count}')
            if not path.exists():
                return str(path)
            count += 1

def dump(msg) -> None:
    if not DEBUG:
        return

    print(f'{msg}')