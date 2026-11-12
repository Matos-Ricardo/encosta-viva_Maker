"""Executar em Utilitarios > Scripts do Autodesk Fusion; cria documentos novos."""
import adsk.core,adsk.fusion,os,json,traceback,math
BASE=os.path.dirname(os.path.realpath(__file__))
def point(x,y,z=0):return adsk.core.Point3D.create(x/10,y/10,z/10)
def vec(a):return adsk.core.Vector3D.create(*a)
def run(context):
    app=adsk.core.Application.get();ui=app.userInterface
    try:
        parts=json.load(open(os.path.join(BASE,'pecas.json'),encoding='utf-8'))
        log={};assembled=None
        for flat in (False,True):
            doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            doc.name='MODELO 02 - ENCAIXES - '+('Pecas para corte' if flat else 'Robo Patins - dois servos')
            if not flat:assembled=doc
            d=adsk.fusion.Design.cast(app.activeProduct);d.designType=adsk.fusion.DesignTypes.ParametricDesignType
            d.unitsManager.distanceDisplayUnits=adsk.fusion.DistanceUnits.MillimeterDistanceUnits
            d.userParameters.add('mdf',adsk.core.ValueInput.createByString('3 mm'),'mm','Espessura; contornos definidos no gerador preparar.py.')
            for name,value in [('altura_total',252),('cabeca_largura',146),('cabeca_altura',84),('tronco_altura',112),('tronco_ombros',132),('tronco_cintura',100),('tronco_profundidade',68)]:
                d.userParameters.add(name,adsk.core.ValueInput.createByString(str(value)+' mm'),'mm','Referencia do modelo; regenerar para alterar contornos.')
            root=d.rootComponent;rows=[]
            appearance=None
            try:
                template=app.materialLibraries.itemByName('Fusion 360 Appearance Library').appearances.itemByName('Paint - Enamel Glossy (Yellow)')
                if template:appearance=d.appearances.addByCopy(template,'MDF - Modelo 02');appearance.appearanceProperties.itemById('generic_diffuse').value=adsk.core.Color.create(174,133,76,255)
            except:pass
            for p in parts:
                tr=adsk.core.Matrix3D.create()
                if flat:tr.translation=vec([p['flat'][0]/10,p['flat'][1]/10,0])
                else:
                    u=p['u'];v=p['v'];n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
                    tr.setWithCoordinateSystem(point(*p['origin']),vec(u),vec(v),vec(n))
                occ=root.occurrences.addNewComponent(tr);comp=occ.component;comp.name=p['id']
                comp.attributes.add('Modelo02','montagem',p['note'])
                sk=comp.sketches.add(comp.xYConstructionPlane);sk.name=p['id']+'_CORTE';sk.isComputeDeferred=True
                for poly in p['loops']:
                    for i,a in enumerate(poly):
                        line=sk.sketchCurves.sketchLines.addByTwoPoints(point(*a),point(*poly[(i+1)%len(poly)]));line.isFixed=True
                sk.isComputeDeferred=False
                profile=max((sk.profiles.item(i) for i in range(sk.profiles.count)),key=lambda q:q.areaProperties().area)
                ext=comp.features.extrudeFeatures.addSimple(profile,adsk.core.ValueInput.createByString('mdf'),adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                ext.name=p['id']+'_MDF3';body=ext.bodies.item(0);body.name=p['id'];sk.isVisible=False
                if appearance:body.appearance=appearance
                rows.append(dict(id=p['id'],volume_mm3=body.volume*1000,esperado_mm3=p['area']*3,erro_mm3=abs(body.volume*1000-p['area']*3)))
                adsk.doEvents()
            root.attributes.add('Modelo02','nota','Modelo novo. MDF 3mm. Dois suportes SG90 provisórios; medir motores e cruzetas antes do corte. Montagem por cola e tampa M3. Não é validação mecânica do conjunto motorizado.')
            d.computeAll();report={'pecas':rows,'interferencias':None}
            if not flat:
                try:
                    objects=adsk.core.ObjectCollection.create()
                    for occ in root.occurrences:objects.add(occ)
                    inp=d.createInterferenceInput(objects);inp.areCoincidentFacesIncluded=False
                    hits=d.analyzeInterference(inp);inter=[]
                    if hits:
                        for i in range(hits.count):
                            h=hits.item(i)
                            inter.append(dict(a=h.entityOne.name,b=h.entityTwo.name,volume_mm3=h.interferenceBody.volume*1000))
                    report['interferencias']=inter
                except Exception as exc:report['erro_interferencia']=str(exc)
            camera=app.activeViewport.camera;camera.cameraType=adsk.core.CameraTypes.OrthographicCameraType
            if flat:
                camera.eye=point(350,200,900);camera.target=point(350,200,0);camera.upVector=vec([0,1,0])
            else:
                camera.eye=point(430,-750,390);camera.target=point(0,25,126);camera.upVector=vec([0,0,1])
            camera.isFitView=True;app.activeViewport.camera=camera;app.activeViewport.fit();app.activeViewport.refresh()
            name='MODELO_02_PECAS_PLANAS' if flat else 'MODELO_02_MONTADO'
            ex=d.exportManager;ex.execute(ex.createFusionArchiveExportOptions(os.path.join(BASE,name+'.f3d')))
            if not flat:ex.execute(ex.createSTEPExportOptions(os.path.join(BASE,name+'.step')))
            app.activeViewport.saveAsImageFile(os.path.join(BASE,name+'.png'),1600,1200)
            log['plano' if flat else 'montado']=report
        assembled.activate();app.activeViewport.fit();app.activeViewport.refresh()
        json.dump(log,open(os.path.join(BASE,'verificacao_fusion.json'),'w',encoding='utf-8'),indent=2)
        ui.messageBox('Modelo 02 criado: '+str(len(parts))+' placas MDF.\nMontagem e vista plana em documentos separados.\nArquivos salvos em:\n'+BASE,'Modelo 02 - concluido')
    except:
        error=traceback.format_exc();open(os.path.join(BASE,'erro_fusion.txt'),'w',encoding='utf-8').write(error);ui.messageBox(error)
