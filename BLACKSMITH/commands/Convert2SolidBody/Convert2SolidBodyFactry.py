import traceback
import adsk
import adsk.core as core
import adsk.fusion as fusion
import math

def to_solidBody(
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
        face: fusion.BRepFace,
        comp: fusion.Component,
        occ: fusion.Occurrence,
    ) -> fusion.Sketch:

        skt: fusion.Sketch = None
        if occ:
            skt = comp.sketches.addWithoutEdges(face, occ)
        else:
            skt = comp.sketches.addWithoutEdges(face)

        return skt


    def create_profile_axis(
        skt: fusion.Sketch,
        face: fusion.BRepFace,
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

        vertex: fusion.BRepVertex = face.vertices[0]
        sktPnt: fusion.SketchPoint = skt.project(vertex)[0]

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

        objs: core.ObjectCollection = core.ObjectCollection.create()
        objs.add(p1)
        objs.add(midPnt)
        objs.add(p2)

        sktFits: fusion.SketchFittedSplines = skt.sketchCurves.sketchFittedSplines
        sktFits.add(objs)

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


    def delete_nurbs_face(
        comp: fusion.Component,
        body: fusion.BRepBody
    ) -> None:

        nurbsLst = [f for f in body.faces
            if f.geometry.objectType == core.NurbsSurface.classType()]

        delFeats: fusion.DeleteFaceFeatures = comp.features.deleteFaceFeatures
        delFeats.add(nurbsLst[0])

    # *****

    if not body.isSheetMetal:
        return

    radius = 0.001

    app: core.Application = core.Application.get()
    des: fusion.Design = app.activeProduct
    tl: fusion.Timeline = des.timeline

    startMarker = tl.markerPosition

    occ: fusion.Occurrence = body.assemblyContext

    flatFace: fusion.BRepFace = get_flat_face(body)
    if not flatFace:
        return

    comp: fusion.Component = body.parentComponent

    sketch: fusion.Sketch = create_sketch(flatFace, comp, occ)

    prof, axis = create_profile_axis(sketch, flatFace, radius)

    solidBody: fusion.BRepBody = create_revolve(comp, prof, axis)

    combBody: fusion.BRepBody = create_combine(
        comp,
        solidBody,
        body
    )

    delete_nurbs_face(comp, combBody)

    endMarker = tl.markerPosition - 1
    try:
        tl.timelineGroups.add(startMarker, endMarker)
    except:
        pass