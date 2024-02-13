import adsk.core, adsk.fusion
import os
import math
from ...lib import fusion360utils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface

#### 
# Feedback:
# Plugin creates a new window for some reason, includes prior history
# Need to handle self intersections in a better way.

# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'Virtual Wire Bender'
CMD_Description = ''
string_commands = ''
# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'
new_run=True
# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []

# previous bendscript timeline groups 
bendscript_timeline_group = None

class WireBender:
    def __init__(self):
        self.points = [[0, 0, 0]]  # Starting point
        self.command_string="" #list of commands
    def __del__(self):
        print('deleted')

    def feed(self, f):
        last_point = self.points[-1]
        new_point = [last_point[0] + f/10, last_point[1], last_point[2]]
        self.points.append(new_point)

    def rotate(self, angle):
        angle = -angle
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
                    for k in range(iter-1):    
                        for j in range(start, end):
                            if commands[j].strip():
                                parts = commands[j].split()
                                if parts[0] == 'feed':
                                    self.feed(float(parts[1]))
                                elif parts[0] == 'rotate':
                                    self.rotate(math.radians(float(parts[1])))
                                elif parts[0] == 'bend':
                                    self.bend(math.radians(float(parts[1])))
                    i=i+1
                elif parts[0] == 'end':
                    next
                else:
                    futil.log(f'{CMD_NAME}: the command {parts[0]} is not recognized')
                    return




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
def add_toolhead():
    if new_run:
        rootComp = app.activeProduct.rootComponent
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'tool.obj')
        returnValue = rootComp.meshBodies.add(filename, 1)
        # Create a collection of entities for move
        features = rootComp.features
        # Create a collection of entities for move
        bodies = adsk.core.ObjectCollection.create()
        for i in range(returnValue.count):
            bodies.add(returnValue.item(i))
        
        # Create a transform to do move
        vector = adsk.core.Vector3D.create(0.0, 10.0, 0.0)
        transform = adsk.core.Matrix3D.create()
        rotX = adsk.core.Matrix3D.create()
                # Change the transform data by rotating around Z+ axis

        rotX.setToRotation(-math.pi/2, adsk.core.Vector3D.create(0,0,1), adsk.core.Point3D.create(0,0,0))
        transform.transformBy(rotX)
        #transform.translation = vector

        # Create a move feature
        moveFeats = features.moveFeatures
        moveFeatureInput = moveFeats.createInput2(bodies)
        moveFeatureInput.defineAsFreeMove(transform)
        moveFeats.add(moveFeatureInput)



# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    global new_run
    add_toolhead()
    new_run = False
    futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    

    # commands text box input.
    inputs.addTextBoxCommandInput('text_box', 'enter bendscript', string_commands, 10, False)

    # wire diameter imput
    defaultLengthUnits = app.activeProduct.unitsManager.defaultLengthUnits
    default_value = adsk.core.ValueInput.createByString('1.6')
    inputs.addValueInput('value_input', 'Wire Diam.', defaultLengthUnits, default_value)

    
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    # futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # Get the root component of the active design.
    global string_commands
    global bendscript_timeline_group

    design = app.activeProduct
    rootComp = design.rootComponent
    inputs = args.command.commandInputs
    
    #get info form the user
    text_box: adsk.core.TextBoxCommandInput = inputs.itemById('text_box')
    value_input: adsk.core.ValueCommandInput = inputs.itemById('value_input')

    # wrap in a timeline group
    timeline = design.timeline
    string_commands =text_box.text
    command_text = text_box.text
    wire_diameter = value_input.value

    if bendscript_timeline_group:
        bendscript_timeline_group.deleteMe(deleteGroupAndContents=True)

    timeline_start_marker = timeline.markerPosition
    create_wire(rootComp, command_text, wire_diameter)

    final_timeline_pos = timeline.markerPosition - 1
    timeline_group = timeline.timelineGroups.add(timeline_start_marker, final_timeline_pos)
    timeline_group.name = 'Bendscript Render'

    # hold the last timeline group in application memory
    bendscript_timeline_group = timeline_group

    return

def create_wire(component, command_text, wire_diameter):

    sketches = component.sketches
    xyPlane = component.xYConstructionPlane
    sketch = sketches.add(xyPlane)
    lines = sketch.sketchCurves.sketchLines
    wire_bender = WireBender()
    wire_bender.parse_commands(command_text)
    points=wire_bender.points
    lines_seg=[]
    # create lines from the points
    for i in range(len(points)-1):
        startpoint = adsk.core.Point3D.create(-(points[i][0]-points[-1][0]), -(points[i][1]-points[-1][1]), -(points[i][2]-points[-1][2]))
        endpoint = adsk.core.Point3D.create(-(points[i+1][0]-points[-1][0]), -(points[i+1][1]-points[-1][1]), -(points[i+1][2]-points[-1][2]))
        line=lines.addByTwoPoints(startpoint, endpoint)
        lines_seg.append(line)
    
    #create fillets between the angled lines
    for i in range(len(lines_seg)-1):
        line1=lines_seg[i]
        line2=lines_seg[i+1]
        try:
            arc = sketch.sketchCurves.sketchArcs.addFillet(line1, line1.endSketchPoint.geometry, line2, line2.startSketchPoint.geometry, 0.33)
        
        except:
            futil.log(f'{CMD_NAME} No fillet to add')
            lines_seg[i].endSketchPoint.merge(lines_seg[i+1].startSketchPoint)
    #contruction plane perpendicular to the path line
    planes = component.constructionPlanes
    planeInput = planes.createInput()
    distance = adsk.core.ValueInput.createByReal(0.0)
    planeInput.setByDistanceOnPath(lines_seg[-1], distance)
    plane1=planes.add(planeInput)
    yzPlane = component.yZConstructionPlane
    # wire diameter profile
    sketch2 = sketches.add(plane1)
    circles = sketch2.sketchCurves.sketchCircles
    circle1 = circles.addByCenterRadius(adsk.core.Point3D.create(points[0][0], points[0][1], points[0][2]), wire_diameter/2)
    #create the sweep
    prof = sketch2.profiles.item(0)
    path = component.features.createPath(lines_seg[-1])
    sweeps = component.features.sweepFeatures
    sweepInput = sweeps.createInput(prof,path, adsk.fusion.FeatureOperations.NewComponentFeatureOperation)
    # sweepInput.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
    try:
        sweep = sweeps.add(sweepInput)
    except:
        futil.log(f'{CMD_NAME}: Try reducing the size of the wire, removing regions of high curvature from the path')
    return

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
