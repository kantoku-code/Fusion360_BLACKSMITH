import traceback
import adsk
import adsk.core as core
import adsk.fusion as fusion
import math
from ... import config

def convert_solidBody(
    body: fusion.BRepBody,
    isCreateComponent: bool,
) -> None:

    solid: fusion.BRepBody = _to_solidBody(body)

    if not isCreateComponent:
        return

    parentComp: fusion.Component = solid.parentComponent
    beforeTokens = [o.entityToken for o in parentComp.allOccurrences]
    moveBody: fusion.BRepBody = solid.createComponent()


    diffOccs = [occ for occ in parentComp.allOccurrences
        if occ.entityToken not in beforeTokens]

    if len(diffOccs) < 1:
        return

    occ: fusion.Occurrence = diffOccs[0]
    proxyBody: fusion.BRepBody = moveBody.createForAssemblyContext(occ)

    config.convert2SolidBody_dict['body'] = proxyBody


    faces = [f for f in proxyBody.faces if f.geometry.objectType == core.Plane.classType()]
    face: fusion.BRepFace = max(faces, key=lambda f: f.area)

    app: core.Application = core.Application.get()
    sels: core.Selections = app.userInterface.activeSelections
    # sels.clear()
    sels.add(face)

    app: core.Application = core.Application.get()
    ui: core.UserInterface = app.userInterface

    onCommandTerminated = MyCommandTerminatedHandler()
    ui.commandTerminated.add(onCommandTerminated)
    config.convert2SolidBody_dict['handler'] = onCommandTerminated


class MyCommandTerminatedHandler(adsk.core.ApplicationCommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args: core.ApplicationCommandEventArgs):
        app: core.Application = core.Application.get()
        ui: core.UserInterface = app.userInterface

        if ui.activeCommand != f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_conv2solid':
            return

        body: fusion.BRepBody = config.convert2SolidBody_dict['body']

        faces = [f for f in body.faces if f.geometry.objectType == core.Plane.classType()]
        face: fusion.BRepFace = max(faces, key=lambda f: f.area)

        sels: core.Selections = app.userInterface.activeSelections
        sels.clear()
        sels.add(face)

        cmdDef: core.CommandDefinition = ui.commandDefinitions.itemById('ConvertToSheetMetalCmd')
        cmdDef.execute()

        # cmds = (
        #     # u'Commands.Start ConvertToSheetMetalCmd',
        #     u'NuCommands.CommitCmd',
        # )
        # [app.executeTextCommand(cmd) for cmd in cmds]

        config.convert2SolidBody_dict['handler'] = None


def _to_solidBody(
    body: fusion.BRepBody,
) -> fusion.BRepBody:

    # ****
    def get_flat_face(
        body: fusion.BRepBody,
    ) -> fusion.BRepFace:

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
    ) -> set:

        # *****
        def init_offset_point(
            pnt: fusion.SketchPoint,
            offset: float,
        ) -> fusion.SketchPoint:
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
    ) -> list:

        bodyLst = [b for b in comp.bRepBodies]
        if occ:
            bodyLst = [b.createForAssemblyContext(occ) for b in bodyLst]

        return [b.entityToken for b in bodyLst]


    def remove_body(
        occ: fusion.Occurrence,
        comp: fusion.Component,
        beforeTokens: list,
        targetVolume: float,
    ) -> fusion.BRepBody:

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