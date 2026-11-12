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

class SheetMetalExportFactry():
    """板金ボディからフラットパターンを作成して書き出す。"""
    def __init__(self) -> None:
        """必要なアプリケーション情報と対象一覧を初期化する。"""
        self.app: core.Application = core.Application.get()
        self.sheetInfos = self._get_sheetMetal_body_infos()


    def export_sheetMetal_flatPattern(
        self, sheetBodyIndexList: list[int],
        optionList: list[str],
        folderPath: str,
        useBodyName: bool,
    ) -> list[str]:
        '''
        フラットパターンを作成してエクスポート
        '''
        failures = []
        try:
            self.app.executeTextCommand(u'Transaction.Start sheetmetal_export')
        except Exception as exc:
            return [f'Failed to start the design transaction: {exc}']
        try:
            for idx in sheetBodyIndexList:
                try:
                    info: dict = self.sheetInfos[idx]
                    body: fusion.BRepBody = info['native']
                    label = f'{body.parentComponent.name} / {body.name}'
                except Exception as exc:
                    failures.append(f'body #{idx}: {exc}')
                    continue

                try:
                    flat: fusion.FlatPattern = self._create_flatPattern(body)
                except Exception as exc:
                    for suffix in optionList:
                        failures.append(f'{label} [{suffix}]: flat pattern: {exc}')
                    continue

                for suffix in optionList:
                    path = None
                    try:
                        path = self._get_path(info, folderPath, SUFFIX_MAP[suffix], useBodyName)
                        if suffix == 'DXF':
                            self._export_dxf(path, flat)
                        elif suffix == 'SAT':
                            self._export_sat(path, flat)
                        else:
                            raise ValueError(f'Unsupported format: {suffix}')
                    except Exception as exc:
                        failures.append(f'{label} [{suffix}] {path or "(path unavailable)"}: {exc}')
                        if path is not None:
                            try:
                                pathlib.Path(path).unlink(missing_ok=True)
                            except OSError as cleanup_exc:
                                failures.append(f'{path}: cleanup failed: {cleanup_exc}')
        finally:
            try:
                self.app.executeTextCommand(u'Transaction.Abort')
            except Exception as exc:
                failures.append(f'Failed to restore the design transaction: {exc}')

        return failures


    def _create_flatPattern(self, body: fusion.BRepBody) -> fusion.FlatPattern:
        '''
        フラットパターン作成
        '''
        comp: fusion.Component = body.parentComponent
        flat: fusion.FlatPattern = comp.flatPattern
        if flat:
            flatProd: fusion.FlatPatternProduct = flat.parentComponent.parentDesign
            flatProd.deleteMe()

        flatFaces = [f for f in body.faces
            if f.geometry.objectType == core.Plane.classType()]
        if not flatFaces:
            raise ValueError('No planar face is available')
        targetFace: fusion.BRepFace = max(flatFaces, key=lambda f: f.area)
        created = comp.createFlatPattern(targetFace)
        if not created:
            raise RuntimeError('Flat pattern creation failed')
        return created


    def _create_sheet_info(self, body: fusion.BRepBody) -> dict[str, object]:
        '''
        シートメタルボディ情報
        '''
        return {
            'id': body.entityToken,
            'native': body,
            'show': False
        }


    def _get_sheetMetal_body_infos(self) -> list[dict[str, object]]:
        '''
        シートメタルボディの取得
        '''
        def get_unique_list(bodyLst: list[fusion.BRepBody]) -> list[fusion.BRepBody]:
            """同じネイティブボディを重複なく集める。"""
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
        if not tmpMgr.exportToFile(bodyLst, path):
            raise RuntimeError('SAT export returned false')


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
        if not expMgr.execute(dxfOpt):
            raise RuntimeError('DXF export returned false')


    def _get_path(self, info: dict[str, object], folderPath: str, suffix: str, useBodyName: bool) -> str:
        '''
        ユニークなファイルパス取得
        '''

        def get_stem_name(info: dict[str, object]) -> str:
            """出力ファイル名に使う安全な名前を作る。"""
            body: fusion.BRepBody= info['native']
            comp: fusion.Component = body.parentComponent
            rule: fusion.SheetMetalRule = comp.activeSheetMetalRule
            stem = f'{comp.name}-{rule.name}-{rule.thickness.expression}'
            if useBodyName:
                stem = f'{body.name}-{stem}'

            return re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', stem).rstrip(' .')

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
