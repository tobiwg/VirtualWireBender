import adsk.core, adsk.fusion
import os
import math
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'Virtual Wire Bender'
CMD_Description = ''

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

class WireBender:
    def __init__(self):
        self.points = [[0, 0, 0]]  # Starting point
        self.command_string="" #list of commands

    def feed(self, f):
        last_point = self.points[-1]
        new_point = [last_point[0] + f, last_point[1], last_point[2]]
        self.points.append(new_point)

    def rotate(self, angle):
        rotation_matrix = [[1, 0, 0],
                           [0, math.cos(angle), -math.sin(angle)],
                           [0, math.sin(angle), math.cos(angle)]]

        rotated_points = []
        for point in self.points:
            rotated_point = [
                point[0] * rotation_matrix[0][0] + point[1] * rotation_matrix[1][0] + point[2] * rotation_matrix[2][0],
                point[0] * rotation_matrix[0][1] + point[1] * rotation_matrix[1][1] + point[2] * rotation_matrix[2][1],
                point[0] * rotation_matrix[0][2] + point[1] * rotation_matrix[1][2] + point[2] * rotation_matrix[2][2]
            ]
            rotated_points.append(rotated_point)

        self.points = rotated_points

    def bend(self, angle):
        rotation_matrix = [[math.cos(angle), -math.sin(angle),0],
                           [math.sin(angle), math.cos(angle), 0],
                           [0, 0, 1]]

        rotated_points = []
        for point in self.points:
            rotated_point = [
                point[0] * rotation_matrix[0][0] + point[1] * rotation_matrix[1][0] + point[2] * rotation_matrix[2][0],
                point[0] * rotation_matrix[0][1] + point[1] * rotation_matrix[1][1] + point[2] * rotation_matrix[2][1],
                point[0] * rotation_matrix[0][2] + point[1] * rotation_matrix[1][2] + point[2] * rotation_matrix[2][2]
            ]
            rotated_points.append(rotated_point)

        self.points = rotated_points

    def parse_commands(self, command_string):
        self.command_string=command_string
        commands = command_string.split('\n')
        for i in range(len(commands)):
            if commands[i].strip():
                parts = commands[i].split()
                if parts[0] == 'feed':
                    if float(parts[1])<=0:
                        futil.log(f'{CMD_NAME} cannot do feed <= 0')
                        break
                    else:
                        self.feed(float(parts[1]))
                elif parts[0] == 'rotate':
                    self.rotate(math.radians(float(parts[1])))
                elif parts[0] == 'bend':
                    self.bend(math.radians(float(parts[1])))
                elif parts[0] == 'repeat':
                    iter = int(parts[1])
                    start=i+1
                    end_comm = commands[start].split()
                    end=start
                    while(end_comm[0] != 'end'):
                        end_comm = commands[end].split()
                        end=end+1
                    for k in range(iter):    
                        for j in range(start, end):
                            if commands[j].strip():
                                parts = commands[j].split()
                                if parts[0] == 'feed':
                                    self.feed(float(parts[1]))
                                elif parts[0] == 'rotate':
                                    self.rotate(math.radians(float(parts[1])))
                                elif parts[0] == 'bend':
                                    self.bend(math.radians(float(parts[1])))



wire_bender = WireBender()
# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)
    
    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    

    # commands text box input.
    inputs.addTextBoxCommandInput('text_box', 'enter commnds', wire_bender.command_string, 10, False)

    # wire diameter imput
    defaultLengthUnits = app.activeProduct.unitsManager.defaultLengthUnits
    default_value = adsk.core.ValueInput.createByString('3.25')
    inputs.addValueInput('value_input', 'Wire Diam.', defaultLengthUnits, default_value)

    
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    # futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    
    # TODO ******************************** Your code here ********************************
    # Get the root component of the active design.
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = app.activeProduct
    rootComp = design.rootComponent
    sketches = rootComp.sketches
    xyPlane = rootComp.xYConstructionPlane
    sketch = sketches.add(xyPlane)
    inputs = args.command.commandInputs
    lines = sketch.sketchCurves.sketchLines
    #get info form the user
    text_box: adsk.core.TextBoxCommandInput = inputs.itemById('text_box')
    value_input: adsk.core.ValueCommandInput = inputs.itemById('value_input')
    
     

    wire_bender.parse_commands(text_box.text)
    points=wire_bender.points
    lines_seg=[]
    # create lines from the points
    for i in range(len(points)-1):
        startpoint = adsk.core.Point3D.create(points[i][0], points[i][1], points[i][2])
        endpoint = adsk.core.Point3D.create(points[i+1][0], points[i+1][1], points[i+1][2])
        line=lines.addByTwoPoints(startpoint, endpoint)
        lines_seg.append(line)
    
    #create fillets between the angled lines
    for i in range(len(lines_seg)-1):
        line1=lines_seg[i]
        line2=lines_seg[i+1]
        try:
            arc = sketch.sketchCurves.sketchArcs.addFillet(line1, line1.endSketchPoint.geometry, line2, line2.startSketchPoint.geometry, value_input.value/2)
        
        except:
            # futil.log(f'{CMD_NAME} No fillet to add')
            lines_seg[i].endSketchPoint.merge(lines_seg[i+1].startSketchPoint)
    #contruction plane perpendicular to the path line
    planes = rootComp.constructionPlanes
    planeInput = planes.createInput()
    distance = adsk.core.ValueInput.createByReal(0.0)
    planeInput.setByDistanceOnPath(lines_seg[0], distance)
    plane1=planes.add(planeInput)
    yzPlane = rootComp.yZConstructionPlane
    # wire diameter profile
    sketch2 = sketches.add(plane1)
    circles = sketch2.sketchCurves.sketchCircles
    circle1 = circles.addByCenterRadius(adsk.core.Point3D.create(points[0][0], points[0][1], points[0][2]), value_input.value/2)
    #create the sweep
    prof = sketch2.profiles.item(0)
    path = rootComp.features.createPath(lines_seg[0])
    sweeps = rootComp.features.sweepFeatures
    sweepInput = sweeps.createInput(prof,path, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
    sweep = sweeps.add(sweepInput)

    # Do something interesting
    # text = text_box.text
    # expression = value_input.expression
    # msg = f'Your text: {text}<br>Your value: {expression}'
    # ui.messageBox(msg)


# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Preview Event')
    inputs = args.command.commandInputs


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs

    # General logging for debug.
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    
    # Verify the validity of the input values. This controls if the OK button is enabled or not.
    valueInput = inputs.itemById('value_input')
    if valueInput.value >= 0:
        args.areInputsValid = True
    else:
        args.areInputsValid = False
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []
