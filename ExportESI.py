# -*- coding: utf-8 -*-

__title__ = "Generate ESI code"
__author__ = "rtm7777"
__license__ = "LGPL 2.1"
__doc__ = "Generate ESI code."
__usage__ = """Select route(s) and activate tool."""

import FreeCAD
App=FreeCAD
import FreeCADGui
Gui=FreeCADGui
from PySide import QtGui
import utilities
import os

class ExportESI():
    """Make ESI code"""

    '''
    Generate position string for travel
    '''
    def generateTravelPosition(self, config, X1, Z1, X2, Z2):
        return "%.2f %.2f %.2f %.2f" % (
            float(X2) - float(config.OriginX),
            float(Z2),
            float(X1) - float(config.OriginX),
            float(Z1)
            )

    '''
    Generate travel
    '''
    def generateTravel(self, config, command, X1, Z1, X2, Z2):
        # - Create position
        position = self.generateTravelPosition(config, X1, Z1, X2, Z2)

        # - Create ESICODE
        return command.replace("G01", "W").replace("{Position}", str(position)).replace(" F{FeedRate}", "").replace(" {WirePower}", "") + "\r\n"

    def generateStartBlock(self, config, start_point):
        ESICODE = ""

        ESICODE += "FX {}\r\n".format(config.HorizontalTravel.getValueAs("mm"))
        ESICODE += "FY {}\r\n".format(config.VerticalTravel.getValueAs("mm"))
        ESICODE += "WL {}\r\n".format(config.FieldWidth.getValueAs("mm"))
        ESICODE += "MX {}\r\n".format(config.BlockLength.getValueAs("mm"))
        ESICODE += "MY {}\r\n".format(config.BlockHeight.getValueAs("mm"))
        ESICODE += "ML {}\r\n".format(config.BlockWidth.getValueAs("mm"))
        ESICODE += "OX {}\r\n".format(config.BlockPosition.y)
        ESICODE += "OY {}\r\n".format(config.BlockPosition.z)
        ESICODE += "OF {}\r\n".format(config.FieldWidth.getValueAs("mm") / 2 - config.BlockWidth.getValueAs("mm") - config.BlockPosition.x)

        return ESICODE
    
    '''
    Generate ESICODE from route
    '''
    def makeESICODE(self, route_list, config):
        # - Task ESICODE buffer
        TASK = []
        start_point = None
        # - Wal all routes
        for route in route_list:
            point_index = 0

            # - Store first point as start point
            if start_point is None: 
                start_point = (route.Offset_L[0], route.Offset_R[0])
            
            for i in range(len(route.Data)):                                
                # - Access item
                object_index = route.Data[i]

                object = route.Objects[object_index]

                points_count = object.PointsCount if i == 0 else object.PointsCount - 1
                # - Step over each point
                for _ in range(points_count):
                    point_l = route.Offset_L[point_index]
                    point_r = route.Offset_R[point_index]

                    # - Generate CUT travel command
                    TASK += self.generateTravel(config, config.CutCommand,
                                                point_l.y, point_l.z, point_r.y, point_r.z, )

                    # - Increase point index
                    point_index += 1

        # ---- Generate startup block
        START = self.generateStartBlock(config, start_point)        

        program = START + ''.join(TASK)

        print ("ESI code generated")

        dialog = QtGui.QFileDialog()
        lastDir = dialog.directory().absolutePath()
        # - Open save file dialog
        save_path, save_filter = dialog.getSaveFileName(None, "Save ESI code", os.path.join(lastDir, route_list[0].Label), "*.esi") # PySide

        # - Check path
        if save_path == "":
            print ("ESI saving aborted (no output file path specified)")
        else:
            try:
                with open(save_path, "w") as f:
                    f.write(program)
                print ("ESI code saved into [%s]" % save_path)
            except Exception:
                App.Console.PrintError("Unable to save ESI code in [" + save_path + "]\n")

    def GetResources(self):
        return {"Pixmap"  : utilities.getIconPath("gcode.svg"), # the name of a svg file available in the resources
                'Accel' : "", # a default shortcut (optional)
                "MenuText": "Generate ESI file",
                "ToolTip" : "Generate ESI file from selected route"}

    def Activated(self):
        # - Get selecttion
        routes = [item.Object for item in Gui.Selection.getSelectionEx()]
        
        job_name = routes[0].JobName

        group = FreeCAD.ActiveDocument.getObject(job_name)
        if group is None:
            QtGui.QMessageBox.critical(None, "Job not found.", "Job [{}] not found in active document.".format(job_name))
            return
        
        # - Get CNC configuration
        config = FreeCAD.ActiveDocument.getObject(group.ConfigName)

        # - Check routes type
        for route in routes:
            if not hasattr(route, "Type") or (route.Type != "Route"):
                QtGui.QMessageBox.critical(None, "Error generating ESI code", "Object type not supported. Check Selected objects.")
        
        hasError = False
        for route in routes:
            if route.Error is not None and len(route.Error) > 0:
                print(route.Error)
                hasError = True
                break

        if hasError:
            QtGui.QMessageBox.critical(None, "Error generating ESI code", "Route data is incorrect. Check Selected routes.")
        else:
            self.makeESICODE(routes, config)

        App.ActiveDocument.recompute()
    
    def IsActive(self):
        if FreeCAD.ActiveDocument is None:
            return False
        else:
            group = Gui.ActiveDocument.ActiveView.getActiveObject("group")
            
            # - if machine is not active, try to select first one in a document
            if group is None or group.Type != "Job":
                group = App.ActiveDocument.getObject("Job")

            if group is not None and group.Type == "Job":
                config = group.getObject(group.ConfigName)

                if config.FiveAxisMachine:
                        return False

                # - Get selecttion
                routes = [item.Object for item in Gui.Selection.getSelectionEx()]

                # - nothing selected
                if len(routes) == 0:
                    return False
                
                # - Check types
                for route in routes:
                    if not hasattr(route, "Type") or (route.Type != "Route"):
                        return False
                    
                job_name = routes[0].JobName
                for  route in routes:
                    if route.JobName != job_name:
                        return False
                    
                return True
            return False
            
Gui.addCommand("MakeESIcode", ExportESI())
