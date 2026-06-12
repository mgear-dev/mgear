"""Rigbits rivet creator"""

import mgear.pymaya as pm


class rivet():
    """Create a rivet

    Thanks to http://jinglezzz.tumblr.com for the tutorial :)
    """

    def create(self, mesh, edge1, edge2, parent, name=None):
        self.sources = {
            'oMesh': mesh,
            'edgeIndex1': edge1,
            'edgeIndex2': edge2
        }

        self.createNodes()
        self.createConnections()
        self.setAttributes()
        if parent:
            pm.parent(self.o_node['locator'].getParent(), parent)
        if name:
            pm.rename(self.o_node['locator'].getParent(), name)

        return self.o_node['locator'].getParent()

    def createNodes(self, *args):
        self.o_node = {
            'meshEdgeNode1': pm.createNode('curveFromMeshEdge'),
            'meshEdgeNode2': pm.createNode('curveFromMeshEdge'),
            'ptOnSurfaceIn': pm.createNode('pointOnSurfaceInfo'),
            'matrixNode': pm.createNode('fourByFourMatrix'),
            'decomposeMatrix': pm.createNode('decomposeMatrix'),
            'loftNode': pm.createNode('loft'),
            'locator': pm.createNode('locator')
        }

    def createConnections(self, *args):
        self.sources['oMesh'].worldMesh.connect(
            self.o_node['meshEdgeNode1'].inputMesh)
        self.sources['oMesh'].worldMesh.connect(
            self.o_node['meshEdgeNode2'].inputMesh)
        self.o_node['meshEdgeNode1'].outputCurve.connect(
            self.o_node['loftNode'].inputCurve[0])
        self.o_node['meshEdgeNode2'].outputCurve.connect(
            self.o_node['loftNode'].inputCurve[1])
        self.o_node['loftNode'].outputSurface.connect(
            self.o_node['ptOnSurfaceIn'].inputSurface)
        self.o_node['ptOnSurfaceIn'].normalizedNormalX.connect(
            self.o_node['matrixNode'].in00)
        self.o_node['ptOnSurfaceIn'].normalizedNormalY.connect(
            self.o_node['matrixNode'].in01)
        self.o_node['ptOnSurfaceIn'].normalizedNormalZ.connect(
            self.o_node['matrixNode'].in02)
        self.o_node['ptOnSurfaceIn'].normalizedTangentUX.connect(
            self.o_node['matrixNode'].in10)
        self.o_node['ptOnSurfaceIn'].normalizedTangentUY.connect(
            self.o_node['matrixNode'].in11)
        self.o_node['ptOnSurfaceIn'].normalizedTangentUZ.connect(
            self.o_node['matrixNode'].in12)
        self.o_node['ptOnSurfaceIn'].normalizedTangentVX.connect(
            self.o_node['matrixNode'].in20)
        self.o_node['ptOnSurfaceIn'].normalizedTangentVY.connect(
            self.o_node['matrixNode'].in21)
        self.o_node['ptOnSurfaceIn'].normalizedTangentVZ.connect(
            self.o_node['matrixNode'].in22)
        self.o_node['ptOnSurfaceIn'].positionX.connect(
            self.o_node['matrixNode'].in30)
        self.o_node['ptOnSurfaceIn'].positionY.connect(
            self.o_node['matrixNode'].in31)
        self.o_node['ptOnSurfaceIn'].positionZ.connect(
            self.o_node['matrixNode'].in32)
        self.o_node['matrixNode'].output.connect(
            self.o_node['decomposeMatrix'].inputMatrix)
        self.o_node['decomposeMatrix'].outputTranslate.connect(
            self.o_node['locator'].getParent().translate)
        self.o_node['decomposeMatrix'].outputRotate.connect(
            self.o_node['locator'].getParent().rotate)
        self.o_node['locator'].attr("visibility").set(False)

    def setAttributes(self):
        self.o_node['meshEdgeNode1'].isHistoricallyInteresting.set(1)
        self.o_node['meshEdgeNode2'].isHistoricallyInteresting.set(1)
        self.o_node['meshEdgeNode1'].edgeIndex[0].set(
            self.sources['edgeIndex1'])
        self.o_node['meshEdgeNode2'].edgeIndex[0].set(
            self.sources['edgeIndex2'])

        self.o_node['loftNode'].reverseSurfaceNormals.set(1)
        self.o_node['loftNode'].inputCurve.set(size=2)
        self.o_node['loftNode'].uniform.set(True)
        self.o_node['loftNode'].sectionSpans.set(3)
        self.o_node['loftNode'].caching.set(True)

        self.o_node['ptOnSurfaceIn'].turnOnPercentage.set(True)
        self.o_node['ptOnSurfaceIn'].parameterU.set(0.5)
        self.o_node['ptOnSurfaceIn'].parameterV.set(0.5)
        self.o_node['ptOnSurfaceIn'].caching.set(True)
