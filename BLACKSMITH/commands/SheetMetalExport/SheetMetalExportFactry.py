import traceback
import adsk
import adsk.core as core
import adsk.fusion as fusion
import pathlib
import re

class SheetMetalExportFactry():
    def __init__(self) -> None:
        self.app: core.Application = core.Application.get()
        self.sheetInfos = self._get_sheetMetal_body_infos()


    def export_sheetMetal_flatPattern(self, sheetBodyIndexList: list, folderPath: str) -> None:
        '''
        フラットパターンを作成してエクスポート
        '''
        self.app.executeTextCommand(u'Transaction.Start sheetmetal_export')
        try:
            for idx in sheetBodyIndexList:
                info: dict = self.sheetInfos[idx]
                try:
                    flat: fusion.FlatPattern = self._create_flatPattern(info['native'])
                    path = self._get_path(info, folderPath)
                    self._export_dxf(path, flat)
                except:
                    continue
        except:
            pass
        finally:
            self.app.executeTextCommand(u'Transaction.Abort')


    # def _all_break_link(self) -> None:
    #     des: fusion.Design = self.app.activeProduct
    #     root: fusion.Component = des.rootComponent

    #     occ: fusion.Occurrence = None
    #     for occ in root.allOccurrences:
    #         if occ.isReferencedComponent:
    #             occ.breakLink()


    def _create_flatPattern(self, body: fusion.BRepBody) -> fusion.FlatPattern:
        '''
        フラットパターン作成
        '''
        comp: fusion.Component = body.parentComponent
        flat: fusion.FlatPattern = comp.flatPattern
        if flat:
            flatProd: fusion.FlatPatternProduct = flat.parentComponent.parentDesign
            flatProd.deleteMe()

        return comp.createFlatPattern(body.faces[0])


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
        expMgr.execute(dxfOpt)


    def _get_path(self, info: dict, folderPath: str) -> str:
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
        suffix = '.dxf'
        path = pathlib.Path(folderPath) / f'{stem}{suffix}'
        if not path.exists():
            return str(path)

        count = 1
        while True:
            path = path.with_stem(f'{stem}_{count}')
            if not path.exists():
                return str(path)
            count += 1