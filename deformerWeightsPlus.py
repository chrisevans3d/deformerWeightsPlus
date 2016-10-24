'''
DeformerWeightsPlus - A bare bones wrapper for the deformerWeights command.
Christopher Evans, Version 0.1, Oct 2016
@author = Chris Evans
version = 0.1

Disclaimer: This was created on Epic Friday, a day where Epic employees can work on whatever we want, but is not owned/managed by Epic Games.
'''

import os
import time
import tempfile
import xml.etree.ElementTree

from PySide import QtGui, QtCore

import maya.cmds as cmds
import maya.OpenMayaUI as mui
import shiboken

def show():
    global deformerWeightsPlusWindow
    try:
        deformerWeightsPlusWindow.close()
    except:
        pass

    deformerWeightsPlusWindow = DeformerWeightsPlus()
    deformerWeightsPlusWindow.show()
    return deformerWeightsPlusWindow

def getMayaWindow():
    ptr = mui.MQtUtil.mainWindow()
    if ptr is not None:
        return shiboken.wrapInstance(long(ptr), QtGui.QWidget)

def removeUnusedInfluences(mesh):
    skin = findRelatedSkinCluster(mesh)
    print skin, mesh
    for inf in cmds.skinCluster(skin, inf=1, q=1):
        if inf not in cmds.skinCluster(skin, weightedInfluence=1, q=1):
            cmds.skinCluster(skin, e=1, ri=inf)

def findRelatedSkinCluster(node):
    skinClusters = cmds.ls(type='skinCluster')

    for cluster in skinClusters:
        geometry = cmds.skinCluster(cluster, q=True, g=True)[0]
        geoTransform = cmds.listRelatives(geometry, parent=True)[0]

        dagPath = cmds.ls(geoTransform, long=True)[0]

        if geoTransform == node:
            return cluster
        elif dagPath == node:
            return cluster


## USER INTERFACE
class DeformerWeightsPlus(QtGui.QDialog):
    def __init__(self, parent=getMayaWindow(), debug=0):
        
        #quick UI stuff
        QtGui.QDialog.__init__(self, parent)
        self.resize(350, 160)
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setContentsMargins(3, 3, 3, 3)
        self.exportBTN = QtGui.QPushButton(self)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setWeight(75)
        font.setBold(True)
        self.exportBTN.setFont(font)
        self.exportBTN.setObjectName("exportBTN")
        self.verticalLayout.addWidget(self.exportBTN)
        self.exportBTN.setText("EXPORT SKIN WEIGHTS")
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.useTempCHK = QtGui.QCheckBox(self)
        self.useTempCHK.setChecked(True)
        self.useTempCHK.setObjectName("useTempCHK")
        self.useTempCHK.setText('Use a tempDir')
        self.horizontalLayout_2.addWidget(self.useTempCHK)
        self.pathLINE = QtGui.QLineEdit(self)
        self.pathLINE.setEnabled(False)
        self.pathLINE.setObjectName("pathLINE")
        self.horizontalLayout_2.addWidget(self.pathLINE)
        self.pathBTN = QtGui.QPushButton(self)
        self.pathBTN.setEnabled(False)
        self.pathBTN.setMaximumSize(QtCore.QSize(25, 16777215))
        self.pathBTN.setObjectName("pathBTN")
        self.pathBTN.setText('...')
        self.horizontalLayout_2.addWidget(self.pathBTN)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.importSkinWeightsBTN = QtGui.QPushButton(self)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setWeight(75)
        font.setBold(True)
        self.importSkinWeightsBTN.setFont(font)
        self.importSkinWeightsBTN.setObjectName("importSkinWeightsBTN")
        self.importSkinWeightsBTN.setText("IMPORT SKIN WEIGHTS")
        self.verticalLayout.addWidget(self.importSkinWeightsBTN)
        self.outputWin = QtGui.QTextEdit(self)
        self.outputWin.setObjectName("outputWin")
        self.verticalLayout.addWidget(self.outputWin)
        self.setWindowTitle("Save/Load skinWeights - (DeformerWeights+)")
        
        #connect UI
        self.exportBTN.clicked.connect(self.exportFn)
        self.importSkinWeightsBTN.clicked.connect(self.importFn)
        
        QtCore.QObject.connect(self.useTempCHK, QtCore.SIGNAL("toggled(bool)"), self.pathLINE.setDisabled)
        QtCore.QObject.connect(self.useTempCHK, QtCore.SIGNAL("toggled(bool)"), self.pathBTN.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(self)
        
        self.output = 'Initialized.\n'
        self.refreshUI()
        self.setTempPath()
        
    def refreshUI(self):
        self.outputWin.setText(self.output)
        
    def exportFn(self):
        meshSel = cmds.ls(sl=1, dag=True, type='mesh')
        if meshSel:
            sdw = SkinDeformerWeights()
            self.output += sdw.saveWeightInfo(fpath=self.pathLINE.text(), meshes=meshSel) + '\n'
            self.refreshUI()
        else:
            cmds.warning('No meshes selected!')
    
    def importFn(self):
        t1 = time.time()
        meshes = cmds.ls(sl=1, dag=True, type='mesh')
        if meshes:
            for mesh in meshes:
                fpath = self.pathLINE.text() + mesh + '.skinWeights'
                if os.path.isfile(fpath):
                    sdw = SkinDeformerWeights(path=fpath)
                    sdw.applyWeightInfo()
                else:
                    cmds.warning('Cannot find file: ' + fpath)
        
            elapsed = time.time() - t1
            self.output += ('Loaded skinWeights for ' + str(len(meshes)) + ' meshes in ' + str(elapsed) + ' seconds.\n')
            self.refreshUI()
        else:
            cmds.warning('No meshes selected!')

    def setTempPath(self):
        tempDir =  tempfile.gettempdir() + '\\maya_weights\\'
        if not os.path.exists(tempDir):
            os.makedirs(tempDir)
        self.pathLINE.setText(tempDir)
        return tempDir

## DEFORMER WEIGHTS CLASS
class SkinDeformerWeights(object):
    def __init__(self, path=None):
        self.path = path
        self.shapes = {}
        self.fileName = None

        if self.path:
            self.parseFile(self.path)

    class skinnedShape(object):
        def __init__(self, joints=None, shape=None, skin=None, verts=None):
            self.joints = joints
            self.shape = shape
            self.skin = skin
            self.verts = verts

    def applyWeightInfo(self, worldSpace=False, normalize=False, debug=False):
        try:
            for shape in self.shapes:
                #make a skincluster using the joints
                if cmds.objExists(shape):
                    ss = self.shapes[shape]
                    skinList = ss.joints

                    newSkinList = [j for j in skinList if cmds.objExists(j)]
                    for j in newSkinList:
                        if cmds.nodeType(j) != 'joint':
                            print 'NOT A JOINT:', j

                    #Report missing joints
                    for joint in skinList:
                        if joint not in newSkinList:
                            print 'JOINT DOES NOT EXIST:', j

                    newSkinList.append(shape)
                    cmds.select(cl=1)
                    cmds.select(newSkinList)

                    lockedNodes = []

                    for obj in newSkinList:
                        if cmds.lockNode(obj, q=1):
                            if debug:
                                print 'NODE LOCKED:', obj
                            cmds.lockNode(obj, lock=False)
                            lockedNodes.append(obj)

                    cluster = cmds.skinCluster(name=ss.skin, tsb=1, mi=8, sm=0)[0]
                    print '>> skinCluster Influences:', cmds.skinCluster(cluster, inf=1, q=1)
                    fname = self.path.split('\\')[-1]
                    dir = self.path.replace(fname,'')

                    meshVerts = cmds.polyEvaluate(shape, v=1)

                    if ss.verts != meshVerts:
                        cmds.warning('WARNING>>> DeformerWeights>>> VertNum mismatch: file: ' + self.path + '[' + str(ss.verts) + '],  ' + shape + ' [' + str(meshVerts) + ']  (Switching to WorldSpace)')
                        worldSpace = True

                    if worldSpace:
                        cmds.deformerWeights(fname, path=dir, deformer=ss.skin, im=1, method='nearest', ws=1)
                        cmds.skinCluster(ss.skin, e=1, forceNormalizeWeights=1)
                    else:
                        #cmds.deformerWeights(fname , path = dir, deformer=ss.skin, im=1, method='index')
                        execMe = 'deformerWeights -import -deformer \"{0}\" -path \"{1}\" \"{2}\";'.format(ss.skin, dir.replace('\\', '\\\\'), fname)
                        mel.eval(execMe)
                        cmds.skinCluster(tsb=1, mi=8, sm=0)
                        cmds.skinCluster(ss.skin, e=1, forceNormalizeWeights=1)
                    #drop selection
                    cmds.select(cl=1)

                    if normalize:
                        cmds.skinPercent(cluster, normalize=True)
                    for obj in lockedNodes:
                        cmds.lockNode(obj, lock=True)
        except Exception as e:
            import traceback
            print(traceback.format_exc())

    def saveWeightInfo(self, fpath, meshes, all=True):
        mayaVer = cmds.about(version=True)
        if 'Preview' in mayaVer:
            mayaVer = 2016
        mayaVer = int(mayaVer)
        t1 = time.time()

        #get skin clusters
        meshDict = {}
        for mesh in meshes:
            #remove unused influences
            removeUnusedInfluences(mesh)

            sc = findRelatedSkinCluster(mesh)
            #not using shape atm, mesh instead
            msh =  cmds.listRelatives(mesh, shapes=1)
            if sc != '':
                meshDict[sc] = mesh
            else:
                cmds.warning('>>>saveWeightInfo: ' + mesh + ' is not connected to a skinCluster!')
        fname = fpath.split('\\')[-1]
        dir = fpath.replace(fname,'')

        if mayaVer > 2016:
            attributes = ['envelope', 'skinningMethod', 'normalizeWeights', 'deformUserNormals', 'useComponents']
            cmds.deformerWeights(fname, path=dir, ex=1, vc=1, attribute=attributes, deformer=meshDict.keys())
            self.parseFile(fpath)
        else:
            for skin in meshDict:
                cmds.deformerWeights(meshDict[skin] + '.skinWeights', path=dir, ex=1, deformer=skin)
                self.parseFile(fpath + meshDict[skin] + '.skinWeights')

        elapsed = time.time() - t1
        retMe = 'Exported skinWeights for ' + str(len(meshes)) +  ' meshes in ' + str(elapsed) + ' seconds.'
        print retMe
        return retMe

    def parseFile(self, path):
        root = xml.etree.ElementTree.parse(path).getroot()

        self.path = path

        #set the header info
        for atype in root.findall('headerInfo'):
            self.fileName = atype.get('fileName')

        for atype in root.findall('weights'):
            jnt = atype.get('source')
            shape = atype.get('shape')
            verts = atype.get('max')
            clusterName = atype.get('deformer')

            if shape not in self.shapes.keys():
                self.shapes[shape] = self.skinnedShape(shape=shape, skin=clusterName, joints=[jnt])
            else:
                s = self.shapes[shape]
                s.joints.append(jnt)

        for atype in root.findall('shape'):
            verts = atype.get('max')
            if verts:
                self.shapes[shape].verts = int(verts)

if __name__ == '__main__':
    show()
