import traceback
import adsk
import adsk.core as core
import adsk.fusion as fusion
import math
from ... import config

def convert_solidBody(
    body: fusion.BRepBody,
    isCreateComponent: bool,
) -> tuple[fusion.BRepBody | None, fusion.BRepBody | None]:

    """板金ボディをソリッドに変換し、必要ならコンポーネントに移す。"""
    solid: fusion.BRepBody = _to_solidBody(body)
    if solid is None:
        return None, None

    if not isCreateComponent:
        return solid, None

    parentComp: fusion.Component = solid.parentComponent
    beforeTokens = [o.entityToken for o in parentComp.allOccurrences]
    moveBody: fusion.BRepBody = solid.createComponent()


    diffOccs = [occ for occ in parentComp.allOccurrences
        if occ.entityToken not in beforeTokens]

    if len(diffOccs) < 1:
        return moveBody, None

    occ: fusion.Occurrence = diffOccs[0]
    proxyBody: fusion.BRepBody = moveBody.createForAssemblyContext(occ)

    return moveBody, proxyBody


def clear_pending_conversion() -> None:
    """保留中の板金変換と終了イベントを解除する。"""
    app: core.Application = core.Application.get()
    handler = config.convert2SolidBody_dict['handler']
    if handler is not None:
        app.userInterface.commandTerminated.remove(handler)
    config.convert2SolidBody_dict['handler'] = None
    config.convert2SolidBody_dict['body'] = None


def set_pending_conversion(body: fusion.BRepBody | None) -> None:
    """コマンド完了後に使うボディとイベントを登録する。"""
    clear_pending_conversion()
    if body is None:
        return
    app: core.Application = core.Application.get()
    handler = MyCommandTerminatedHandler()
    app.userInterface.commandTerminated.add(handler)
    config.convert2SolidBody_dict['body'] = body
    config.convert2SolidBody_dict['handler'] = handler


class MyCommandTerminatedHandler(adsk.core.ApplicationCommandEventHandler):
    """ソリッド変換コマンドの終了を監視する。"""
    def __init__(self) -> None:
        """Fusion の終了イベントハンドラを初期化する。"""
        super().__init__()
    def notify(self, args: core.ApplicationCommandEventArgs) -> None:
        """変換が正常終了したら板金変換コマンドを起動する。"""
        app: core.Application = core.Application.get()
        ui: core.UserInterface = app.userInterface

        if args.commandId != f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_conv2solid':
            return

        body: fusion.BRepBody = config.convert2SolidBody_dict['body']
        clear_pending_conversion()
        if args.terminationReason != core.CommandTerminationReason.CompletedTerminationReason:
            return
        if body is None or not body.isValid:
            return

        try:
            faces = [f for f in body.faces if f.geometry.objectType == core.Plane.classType()]
            if not faces:
                raise RuntimeError('Converted body has no planar face')
            face: fusion.BRepFace = max(faces, key=lambda f: f.area)
            sels: core.Selections = ui.activeSelections
            sels.clear()
            sels.add(face)
            cmdDef: core.CommandDefinition = ui.commandDefinitions.itemById('ConvertToSheetMetalCmd')
            if not cmdDef:
                raise RuntimeError('ConvertToSheetMetalCmd is unavailable')
            cmdDef.execute()
        except Exception:
            app.log(traceback.format_exc())


def _to_solidBody(
    body: fusion.BRepBody,
) -> fusion.BRepBody | None:

    # ****
    """板金ボディと補助形状を結合してソリッドボディを作る。"""
    def get_flat_face(
        body: fusion.BRepBody,
    ) -> fusion.BRepFace | None:

        """面積が最大の平面を取得する。"""
        f: fusion.BRepFace = None
        flatLst = [f for f in body.faces 
            if f.geometry.objectType == core.Plane.classType()]

        if len(flatLst) < 1:
            return None

        return max(flatLst, key = lambda x: x.area)


    def create_sketch(
        comp: fusion.Component,
        occ: fusion.Occurrence,
    ) -> fusion.Sketch:

        """対象コンポーネントの XY 平面にスケッチを作る。"""
        plane: fusion.ConstructionPlane = comp.xYConstructionPlane
        skt: fusion.Sketch = None
        if occ:
            skt = comp.sketches.addWithoutEdges(plane, occ)
        else:
            skt = comp.sketches.addWithoutEdges(plane)

        return skt


    def create_profile_axis(
        skt: fusion.Sketch,
        length: float,
    ) -> tuple[fusion.Profile, fusion.SketchLine]:

        # *****
        """回転体用の断面と回転軸を作る。"""
        def init_offset_point(
            pnt: fusion.SketchPoint,
            offset: float,
        ) -> fusion.SketchPoint:
            """スケッチ点から Y 方向にずらした点を作る。"""
            skt: fusion.Sketch = pnt.parentSketch

            p: core.Point3D = pnt.geometry.copy()
            p.y += offset

            return skt.sketchPoints.add(p)
        # *****

        sktPnt: fusion.SketchPoint = skt.sketchPoints.add(
            core.Point3D.create(
                100000000,
                100000000,
                0
            )
        )

        p1: core.Point3D = init_offset_point(
            sktPnt,
            length
        )
        p2: core.Point3D = init_offset_point(
            sktPnt,
            -length
        )

        sktLines: fusion.SketchLines = skt.sketchCurves.sketchLines
        line: fusion.SketchLine = sktLines.addByTwoPoints(p1, p2)

        geoConst: fusion.GeometricConstraints = skt.geometricConstraints
        geoConst.addCoincident(sktPnt, line)

        midPnt: core.Point3D = sktPnt.geometry.copy()
        midPnt.x += length

        sktArcs: fusion.SketchArcs = skt.sketchCurves.sketchArcs
        sktArcs.addByThreePoints(
            p1,
            midPnt,
            p2,
        )

        return (skt.profiles[0], line)


    def create_revolve(
        comp: fusion.Component,
        prof: fusion.Profile,
        axis: fusion.SketchLine,
    ) -> fusion.BRepBody:

        """断面を回転させて補助ボディを作る。"""
        revolveFeats: fusion.RevolveFeatures = comp.features.revolveFeatures
        revolveFeatIpt: fusion.RevolveFeatureInput = revolveFeats.createInput(
            prof,
            axis,
            fusion.FeatureOperations.NewBodyFeatureOperation,
        )
        revolveFeatIpt.setAngleExtent(
            True,
            core.ValueInput.createByReal(
                math.radians(360)
            )
        )
        revolveFeat: fusion.RevolveFeature = revolveFeats.add(revolveFeatIpt)

        return revolveFeat.bodies[0]


    def create_combine(
        comp: fusion.Component,
        targetBody: fusion.BRepBody,
        toolBody: fusion.BRepBody,
    ) -> fusion.BRepBody:

        """補助ボディと対象ボディを結合する。"""
        objs: core.ObjectCollection = core.ObjectCollection.create()
        objs.add(toolBody)

        combineFeats: fusion.CombineFeatures = comp.features.combineFeatures
        combineIpt: fusion.CombineFeatureInput = combineFeats.createInput(
            targetBody,
            objs,
        )
        combineFeat: fusion.CombineFeature = combineFeats.add(combineIpt)

        return combineFeat.bodies[0]


    def get_occ_body_tokens(
        occ: fusion.Occurrence,
        comp: fusion.Component,
    ) -> list[str]:

        """対象コンポーネントのボディ識別子を集める。"""
        bodyLst = [b for b in comp.bRepBodies]
        if occ:
            bodyLst = [b.createForAssemblyContext(occ) for b in bodyLst]

        return [b.entityToken for b in bodyLst]


    def remove_body(
        occ: fusion.Occurrence,
        comp: fusion.Component,
        beforeTokens: list[str],
        targetVolume: float,
    ) -> list[fusion.BRepBody]:

        """追加されたボディのうち補助ボディを削除する。"""
        bodyLst = [b for b in comp.bRepBodies]
        if occ:
            bodyLst = [b.createForAssemblyContext(occ) for b in bodyLst]

        diffBodyLst = [b for b in bodyLst if b.entityToken not in beforeTokens]
        removeBody: fusion.BRepBody = min(diffBodyLst, key=lambda b: abs(b.volume - targetVolume))

        keepBody: fusion.BRepBody = [b for b in diffBodyLst if b.entityToken != removeBody.entityToken]

        removeFeats: fusion.RemoveFeatures = comp.features.removeFeatures
        removeFeats.add(removeBody)

        return keepBody
    # *****

    if not body.isSheetMetal:
        return

    radius = 1

    app: core.Application = core.Application.get()
    des: fusion.Design = app.activeProduct
    tl: fusion.Timeline = des.timeline

    startMarker = tl.markerPosition

    occ: fusion.Occurrence = body.assemblyContext

    flatFace: fusion.BRepFace = get_flat_face(body)
    if not flatFace:
        return

    comp: fusion.Component = body.parentComponent

    sketch: fusion.Sketch = create_sketch(comp, occ)

    prof, axis = create_profile_axis(sketch, radius)

    beforeTokens = get_occ_body_tokens(occ, comp)

    solidBody: fusion.BRepBody = create_revolve(comp, prof, axis)
    volume = solidBody.volume

    create_combine(comp, solidBody, body)

    keepBodies = remove_body(occ, comp, beforeTokens, volume)
    keepBody: fusion.BRepBody = keepBodies[0]

    endMarker = tl.markerPosition - 1
    try:
        tl.timelineGroups.add(startMarker, endMarker)
    except:
        pass

    return keepBody
