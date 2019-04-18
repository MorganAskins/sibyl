from PyQt5 import QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pyqtgraph as pg
import pyqtgraph.opengl as gl
import numpy as np
import matplotlib.cm as cm

class SibylHistogram(gl.GLViewWidget):
    '''
    SibylHistogram is a GLViewWidget (3D viewport), which uses the GLMeshItem
    to draw the vertices and faces of the histogram in different colors.
    '''
    App = None
    data  = 0   # Input data to be histogrammed
    xmin  = 0
    xmax  = 5.5
    nbins = 20 # Default binning
    txt   = '( )'
    zoom_y = 1
    zoom_x = 1
    autoMode = True
    def __init__(self, app=None, parent=None):
        if self.App is None:
            if app is not None:
                self.App = app
            else:
                self.App = QtGui.QApplication([])
        super(SibylHistogram,self).__init__()
        self._parent=parent
        self._init_camera()
        self._axes()
        self._menu()
        self.setMouseTracking(True)
        #self.setAutoFillBackground(False)
        self.histMesh = gl.GLMeshItem(smooth=False)
        self.addItem(self.histMesh)
        self.update()

    def _axes(self):
        self.ax = gl.GLGridItem()
        self.ax.setSize(5.5,10,1)
        self.ax.setSpacing(5.5/5, 1, 1)
        self.ax.translate(5.5/2,10/2.,0)
        #self.ax.setSize(x=10)
        #self.ax = gl.GLBoxItem(glOptions='opaque')
        #self.ax.setSize(5.5, 0, 1)
        self.addItem(self.ax)

    def _menu(self):
        self.menu = QMenu()
        # Reset (like auto)
        resetAction = self.menu.addAction("Reset")
        resetAction.triggered.connect(self._autoset)
        # Set auto-mode
        autoModeAction = self.menu.addAction("Auto-coordinates")
        autoModeAction.setCheckable(True)
        if self.autoMode:
            autoModeAction.setChecked(True)
        autoModeAction.triggered.connect(self._toggle_auto)

    def _toggle_auto(self):
        self.autoMode = not self.autoMode

    def _autoset(self):
        # Set best x and y (x to edge, y at 90%)
        x, y = self.screenToWorld( (0, self.height()*0.1) )
        end_x = np.max(self.data)
        self.zoom_x = self.xmax/end_x
        self.zoom_x = np.max([0, self.zoom_x])
        self.resetHist()
        self.zoom_y = y/np.max(self.hy)
        self.resetMesh()

    def update(self):
        super(SibylHistogram,self).update()

    def setData(self, data):
        self.data = data
        if self.autoMode:
            self._autoset()
        else:
            self.resetHist()
            self.resetMesh()

    def resetHist(self):
        hy, hx = np.histogram(self.data, 
                    bins=np.linspace(self.xmin,self.xmax/self.zoom_x,self.nbins), 
                    density=False)
        self.hx = hx
        self.hy = hy

    def resetMesh(self):
        vtx, colrs, faces = self._verts(self.hx*self.zoom_x, self.hy*self.zoom_y)
        self.histMesh.setMeshData(vertexes=vtx, faces=faces, faceColors=colrs)
        self.histMesh.update()
        self._parent.parameters['histXMax'] = self.xmax/self.zoom_x
        if self._parent is not None:
            self._parent.drawColors()

    def _verts(self, x, y):
        # points, N bins -> 3*(N-2)+7
        # for x, [0,0,1,1,1, ..., N, N]
        nbins = len(y)
        x_verts     = np.repeat(x, 3)[1:-1]
        temp_y      = np.repeat(y, 3)
        temp_y[::3] = 0
        y_verts     = np.concatenate([temp_y, [0]])
        z_verts     = np.zeros(x_verts.shape)
        pos = np.array([x_verts, y_verts, z_verts]).T
        # Color stuff
        #clrs = np.repeat(cm.jet(x[:-1]), 2, axis=0)
        #clrs = cm.cividis(np.linspace(0,1,nbins))
        clrs = self._parent.parameters['colorMap'](np.linspace(0, 1, nbins))
        # Faces
        k,j = np.arange(nbins*3), np.arange(nbins*3)
        face1 = k.reshape(nbins,3)
        k[1::3] += 2
        face2 = j.reshape(nbins,3)
    
        face = np.concatenate([face1, face2])
        clrs = np.concatenate([clrs, clrs])
        return pos, clrs, face

    def _init_camera(self):
        # init camera -- this is pseudo 2D
        self.opts['center'] = QVector3D(0, 0, 0)
        self.setCameraPosition(pos=np.array([0, 0, 0]))
        self.opts['elevation'] = 90
        self.opts['distance']  = 350
        self.opts['fov']       = 1
        self.opts['azimuth']   = -90

    def paintGL(self, *args, **kwargs):
        #self.paintEvent(*args, **kwargs)
        super(SibylHistogram,self).paintGL(*args, **kwargs)
        self.drawLegend()
    #    pass

    def paintEvent(self, event, *args, **kwargs):
        #super(SibylHistogram,self).paintGL(*args, **kwargs)
        super(SibylHistogram,self).paintEvent(event, *args, **kwargs)
        #self.drawLegend()


    def drawLegend(self):
        margin = 11
        padding = 6
        self.qglColor(Qt.white)
        self.renderText(0.8*self.width(), 0.1*self.height(), self.txt)

    '''
    Interactive events: mouse, keys, wheel, resize
    '''

    def contextMenuEvent(self, event):
        self.menu.exec_(self.mapToGlobal(event.pos()))

    def resizeEvent(self, event):
        self.plotToBottom()
        if self.autoMode:
            self._autoset()

    def wheelEvent(self, event):
        delta = event.angleDelta().x()
        if delta == 0:
            delta = event.angleDelta().y()
        # Change binning with shift-scroll
        if event.modifiers() & Qt.ShiftModifier:
            self.nbins += delta/20.0
            self.nbins = int(np.max([4, self.nbins]))
            self.resetHist()
        # Pan x-axis with fixed nbins (change xmax)
        elif event.modifiers() & Qt.ControlModifier:
            self.zoom_x *= 1.001**delta
            self.resetHist()
        # Zoom along y-axis
        else:
            self.zoom_y *= 1.001**delta
        self.resetMesh()

    def mouseDoubleClickEvent(self, event):
        if event.button() == 1:
            self._autoset()


    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        mousePos = event.pos()
        x, y = mousePos.x(), mousePos.y()
        mx, my = self.screenToWorld( (x, y) )
        my /= self.zoom_y
        mx /= self.zoom_x
        self.txt = '(%0.2f, %0.2f)'%(mx, my)
        self.update()

    def leaveEvent(self, event):
        super(SibylHistogram,self).leaveEvent(event)
        self.txt = '()'
        self.update()

    def plotToBottom(self):
        self.opts['center'] = QVector3D(0, 0, 0)
        bx, by = self.screenToWorld( (0, self.height() ) )
        self.opts['center'] = QVector3D(-bx*0.9, -by*0.90, 0)

    def worldToScreen(self, world):
        # world is a 4D vector, (x,y,z,w)
        pass

    def screenToWorld(self, screen):
        mx, my = screen
        view_w = self.width()
        view_h = self.height()
        x = 2.0 * mx / view_w - 1.0
        y = 1.0 - (2.0 * my / view_h)
        PMi = self.projectionMatrix().inverted()[0]
        VMi = self.viewMatrix().inverted()[0]
        ray_clip = QVector4D(x, y, -1.0, 1.0)
        ray_eye = PMi * ray_clip
        ray_eye.setW(0)
        # Convert to world coordinates
        ray_world = VMi * ray_eye
        ray_world = QVector3D(ray_world.x(), ray_world.y(), ray_world.z())
        ray_world.normalize()
        origin = np.matrix(self.cameraPosition())
        origin = self.cameraPosition()
        # intercept with XY-plane
        normal = QVector3D(0, 0, 1)
        pzero = QVector3D(0, 0, 0)
        d = self.dot( (pzero - origin), normal ) / self.dot(ray_world, normal)
        intercept = d*ray_world + origin
        return intercept.x(), intercept.y()

    def dot(self, v1, v2):
        return QVector3D.dotProduct(v1, v2)



if __name__ == '__main__':
    import sys
    app = QtGui.QApplication([])
    w = SibylHistogram()
    w.show()
    
    data = np.random.normal(0, 1, 100000)
    w.setData(data)
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
