import arcpy
import types
import string, random, os

import numpy as np

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Weighted Raster Overlay Service Tools"
        self.alias = "wroservice"

        # List of tool classes associated with this toolbox
        self.tools = [CreateWeightedOverlayMosaic,UpdateWROLayerInfo,UpdateWROClassification]

class UpdateWROClassification(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update WRO Layer Classification"
        self.description = "Updates layer classification ranges in a weighted overlay mosaic."
        self.canRunInBackground = False
        #self.mo_flds = ["Title", "Description"]
        self.mo_flds = ["Title", "RangeLabels", "InputRanges", "OutputValues"]
        id = None
        raster_path = None
        min_val = None
        max_val = None


    def getParameterInfo(self):
        """Define parameter definitions"""
        in_mosaic = arcpy.Parameter(
        displayName="Input Weighted Overlay Mosaic",
        name="inMosaic",
        datatype="DEMosaicDataset",
        parameterType="Required",
        direction="Input")

        wro_lyr=arcpy.Parameter(
        displayName="WRO Mosaic Layer",
        name="in_mosaic_row",
        datatype="GPString",
        parameterType="Required",
        direction="Input")
        wro_lyr.filter.type = "ValueList"

        wro_title = arcpy.Parameter(
        displayName="WRO Layer Title",
        name="wroTitle",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        class_method = arcpy.Parameter(
        displayName="Classification Method",
        name="classMethod",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")
        class_method.filter.type = "ValueList"
        class_method.filter.list = ["Equal Interval", "Quantiles"]

        num_breaks=arcpy.Parameter(
        displayName="Number of Breaks",
        name="numBreaks",
        datatype="GPLong",
        parameterType="Optional",
        direction="Input")
        num_breaks.filter.type = "ValueList"
        num_breaks.filter.list = [2,3,4,5,6,7,8,9]

        mosaic_lyr_data = arcpy.Parameter(
        displayName="Mosaic Layer Data",
        name="mosaicLayerData",
        datatype="GPValueTable",
        parameterType="Required",
        direction="Input")
        mosaic_lyr_data.columns = [['GPString','Range Label'],['GPDouble', 'Min Range'], ['GPDouble', 'Max Range'],['GPLong', 'Suitability Value']]
        mosaic_lyr_data.filters[3].type = "ValueList"
        mosaic_lyr_data.filters[3].list = [0,1,2,3,4,5,6,7,8,9]

        out_mosaic=arcpy.Parameter(
        displayName="Output Mosaic Dataset",
        name="outMosaic",
        datatype="DEMosaicDataset",
        parameterType="Derived",
        direction="Output")

        out_mosaic.parameterDependencies=[in_mosaic.name]
        out_mosaic.schema.clone=True

        params = [in_mosaic ,wro_lyr, wro_title, class_method, num_breaks, mosaic_lyr_data, out_mosaic]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def calculateQuantiles(self, num_classes, raster_array):
        break_list = []
        if num_classes >= 1 and num_classes <= 9:
            quantile_step = 100/num_classes
            perc_break = 0
            break_val = 0
            for i in range(0, num_classes):
                break_val = np.percentile(raster_array, perc_break, interpolation="midpoint")
                break_list.append(break_val)
                perc_break += quantile_step

        return break_list



    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        raster_tbl = os.path.join("in_memory", "raster_paths")
        if parameters[0].value:
            if not parameters[0].hasBeenValidated and parameters[0].altered:
                if arcpy.Exists(raster_tbl):
                    arcpy.Delete_management(raster_tbl)
                # Get raster file
                arcpy.ExportMosaicDatasetPaths_management(parameters[0].value, raster_tbl)

                # Clear other params
                parameters[1].value = None
                parameters[2].value = None
                parameters[3].value = None
                parameters[4].value = None
                parameters[5].value = None

            # Get list of layer names and populate WRO Mosaic Layer param
            names = []
            with arcpy.da.SearchCursor(parameters[0].value, "Name") as cur:
                for row in cur:
                    names.append(row[0])
            parameters[1].filter.list = names

            if not parameters[1].hasBeenValidated and parameters[1].altered:
            #if not parameters[5] or not parameters[5].altered or (parameters[1].altered and not parameters[1].hasBeenValidated):
                # Clear other params
                parameters[2].value = None
                parameters[3].value = None
                parameters[4].value = None
                parameters[5].value = None

                # Check for required mosaic dataset fields
                missing_flds = []
                fld_list = [fld.name for fld in arcpy.ListFields(parameters[0].value)]
                for fld in self.mo_flds:
                    if fld not in fld_list:
                        missing_flds.append(fld)
                # If any fields are missing, show them in an error message
                if missing_flds:
                    parameters[0].setErrorMessage("Missing fields {} in {}".format(missing_flds, parameters[0].valueAsText))
                    return


                # Get Layer Title and Mosaic Layer Data values for user-selected Mosaic Layer (param 1)
                if parameters[1].value: # and parameters[1].altered:
                    where = "Name = '" + parameters[1].valueAsText + "'"
                    ##["Title", "RangeLabels", "InputRanges", "OutputValues"]
                    with arcpy.da.SearchCursor(parameters[0].value, ["Title", "OID@", "RangeLabels", "InputRanges", "OutputValues"], where) as cur:
                        row = cur.next()
                        global id
                        id = row[1]
                        self._labels = row[2]
                        self._ranges = row[3]
                        self._output_values = row[4]

                        if row[0]:
                            parameters[2].value = row[0]
                        if row[2]:
                            label_list = row[2].split(",")
                        if row[3]:
                            range_list = row[3].split(",")
                        if row[4]:
                            suitability_list = row[4].split(",")

                    # Write values to UI value table
                    out_values = ""
                    for i in range(len(label_list)):
                        out_values += ('"{}" {} {} {} {}').format(label_list[i], range_list[i*2], range_list[i*2+1], suitability_list[i], ";")

                    parameters[5].value = out_values


            # Update min/max ranges based on classification method and number of breaks
            if (not parameters[3].hasBeenValidated and parameters[3].altered) or (not parameters[4].hasBeenValidated and parameters[4].altered): # or (not parameters[1].hasBeenValidated and parameters[1].altered):
                where = "SourceOID = " + str(id)
                with arcpy.da.SearchCursor(raster_tbl, ["Path"], where) as cur:
                    for row in cur:
                        global raster_path
                        raster_path = row[0]
                        if arcpy.Exists(raster_path):
                            if parameters[3].value and parameters[4].value:
                                # Get min/max values
                                global min_val
                                global max_val
                                min_val = float(arcpy.GetRasterProperties_management(raster_path, "MINIMUM").getOutput(0))
                                max_val = float(arcpy.GetRasterProperties_management(raster_path, "MAXIMUM").getOutput(0))
                                if id:
                                    if parameters[3].value == "Quantiles":
                                        # Get class breaks
                                        class_break = 100.0/parameters[4].value
                                        # Create numpy array
                                        arr = arcpy.RasterToNumPyArray(raster_path)
                                        break_list = self.calculateQuantiles(parameters[4].value, arr)
                                        break_list.append(max_val)
                                    else: # Equal interval
                                        break_list = list(np.linspace(min_val, max_val, parameters[4].value+1))
                                    if break_list:
                                        count = 0
                                        out_values = ""
                                        while count < len(break_list) - 1:
                                            out_values += ('"{}" {} {} {} {}').format(str(break_list[count]) + " - " + str(break_list[count + 1]),
                                                                                      break_list[count], break_list[count + 1], 5, ";")
                                            count += 1
                                        # Create values in value table
                                        parameters[5].value = out_values


        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        # Check for required mosaic dataset fields
        if parameters[0].value and not parameters[0].hasBeenValidated:
            missing_flds = []
            fld_list = [fld.name for fld in arcpy.ListFields(parameters[0].value)]
            for fld in self.mo_flds:
                if fld not in fld_list:
                    missing_flds.append(fld)
            # If any fields are missing, show them in an error message
            if missing_flds:
                parameters[0].setErrorMessage("Missing fields {} in {}".format(missing_flds, parameters[0].valueAsText))

        # Verify that raster dataset exists
        if parameters[1].value and not parameters[1].hasBeenValidated and parameters[3].value and parameters[4].value:
            if raster_path:
                if not arcpy.Exists(raster_path):
                    parameters[1].setErrorMessage("Raster not found: " + str(raster_path))

        # Verify max value of range matches min value of next range
        if parameters[3].value and parameters[4].value: # and parameters[5].altered:
            range_list = []
            for val in parameters[5].value:
                range_list.append(val[1])
                range_list.append(val[2])
            count = 1
            while count < (len(range_list) - 1):
                min = range_list[count]
                max = range_list[count + 1]
                if min != max:
                    parameters[5].setErrorMessage("Range values mismatch: " + str(min) + " and " + str(max))
                    break
                count += 2

            # Verify that break ranges do not extend beyond min/max values
            value_tbl = parameters[5].value
            if str(value_tbl[0][1]) != str(min_val):
                parameters[5].setErrorMessage("Minimum range value must match minimum cell value of raster: " + str(min_val))
            elif str(value_tbl[-1][2]) != str(max_val):
                parameters[5].setErrorMessage("Maximum range value must match maximum cell value of raster: " + str(value_tbl[-1][2]) + " " + str(max_val))

            # Do not allow user to create or delete any rows in the value table
            if len(value_tbl) != parameters[4].value:
                parameters[5].setErrorMessage("Number of rows in value table must equal number of class breaks")

        return


    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Read parameters from UI
        mosaic_dataset = parameters[0].value
        name = parameters[1].valueAsText
        title = parameters[2].valueAsText
        value_tbl = parameters[5].value

        # Where clause
        where = "Name = '" + name + "'"

        # Read values from value table
        ranges = ""
        range_labels = ""
        output_values = ""
        for val in value_tbl:
            ranges += str(val[1]) + "," + str(val[2]) + ","
            range_labels += str(val[0]) + ","
            output_values += str(val[3]) + ","
        ranges = ranges[:-1]
        range_labels = range_labels[:-1]
        output_values = output_values[:-1]
##        arcpy.AddMessage(ranges)
##        arcpy.AddMessage(range_labels)
##        arcpy.AddMessage(output_values)

        # Check for user changes
        changes = False
        ##["Title", "RangeLabels", "InputRanges", "OutputValues"]
        with arcpy.da.SearchCursor(mosaic_dataset, self.mo_flds, where) as cur:
            row = cur.next()
            if title != row[0]:
                changes = True
                arcpy.AddMessage("Title:")
                arcpy.AddMessage("\tOriginal: " + row[0])
                arcpy.AddMessage("\tNew: " + title)
            if range_labels != row[1].replace(", ", ","):
                changes = True
                arcpy.AddMessage("Range Labels:")
##                arcpy.AddMessage("\tOriginal: " + row[1])
##                arcpy.AddMessage("\tNew: " + range_labels)
                self.showMessages(row[1],range_labels)
            if ranges != row[2]:
                changes = True
                arcpy.AddMessage("InputRanges:")
##                arcpy.AddMessage("\tOriginal: " + row[2])
##                arcpy.AddMessage("\tNew: " + ranges)
                self.showMessages(row[2],ranges)
            if output_values != row[3]:
                changes = True
                arcpy.AddMessage("OutputValues:")
##                arcpy.AddMessage("\tOriginal: " + row[3])
##                arcpy.AddMessage("\tNew: " + output_values)
                self.showMessages(row[3],output_values)

        # Update Mosaic Dataset table with values from tool UI
        if changes:
            if title == "":
                title = None

            # Update record with user-defined values
            ##["Title", "RangeLabels", "InputRanges", "OutputValues"]
            with arcpy.da.UpdateCursor(mosaic_dataset, self.mo_flds, where) as cur:
                for row in cur:
                    row = (title, range_labels, ranges, output_values)
                    cur.updateRow(row)
        else:
            arcpy.AddMessage("No changes found")

        return

    def showMessages(this,rowByIdx,paramTitle):
        if rowByIdx is None:
            arcpy.AddMessage("\tOriginal: Empty")
        else:
            arcpy.AddMessage("\tOriginal: " + rowByIdx)

        if paramTitle is None:
            arcpy.AddMessage("\tNew: Empty")
        else:
            arcpy.AddMessage("\tNew: " + paramTitle)

        return

class UpdateWROLayerInfo(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update WRO Layer Info"
        self.description = "Lets you add descriptive information to a layer in your WRO Mosaic."
        self.canRunInBackground = False
        self.mo_flds = ["Title", "Description", "Url", "Metadata", "NoDataRanges", "NoDataRangeLabels"]


    def getParameterInfo(self):
        """Define parameter definitions"""
        in_mosaic = arcpy.Parameter(
        displayName="Input Weighted Overlay Mosaic",
        name="inMosaic",
        datatype="DEMosaicDataset",
        parameterType="Required",
        direction="Input")

        wro_lyr=arcpy.Parameter(
        displayName="WRO Mosaic Layer",
        name="in_mosaic_row",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        wro_lyr.filter.type = 'ValueList'

        wro_title = arcpy.Parameter(
        displayName="WRO Layer Title",
        name="wroTitle",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        wro_lyr_desc = arcpy.Parameter(
        displayName="WRO Layer Description",
        name="wroLayerDescription",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        wro_lyr_preview_url=arcpy.Parameter(
        displayName="WRO Layer Preview URL",
        name="wroLayerPreviewURL",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        wro_lyr_info_url=arcpy.Parameter(
        displayName="WRO Layer Informational URL",
        name="wroLayerInfoURL",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        wro_lyr_no_data_ranges=arcpy.Parameter(
        displayName="WRO Layer NoData Value",
        name="wroLayerNoDataRanges",
        datatype="GPDouble",
        parameterType="Optional",
        direction="Input")

        # Cam: change to NoData Label instead of No Data Labels?
        wro_lyr_no_data_range_labels=arcpy.Parameter(
        displayName="WRO Layer NoData Label",
        name="wroLayerNoDataRangeLabels",
        datatype="GPString",
        parameterType="Optional",
        direction="Input")

        out_mosaic=arcpy.Parameter(
        displayName="Output Mosaic Dataset",
        name="outMosaic",
        datatype="DEMosaicDataset",
        parameterType="Derived",
        direction="Output")

        out_mosaic.parameterDependencies=[in_mosaic.name]
        out_mosaic.schema.clone=True

        params = [in_mosaic ,wro_lyr, wro_title, wro_lyr_desc, wro_lyr_preview_url,
                  wro_lyr_info_url, wro_lyr_no_data_ranges, wro_lyr_no_data_range_labels, out_mosaic]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            # clear the params
            if parameters[0].altered and not parameters[0].hasBeenValidated:
                parameters[1].value = None
                parameters[2].value = None
                parameters[3].value = None
                parameters[4].value = None
                parameters[5].value = None
                parameters[6].value = None
                parameters[7].value = None

            # Get list of layer names and populate WRO Mosaic Layer param
            names = []
            with arcpy.da.SearchCursor(parameters[0].value, "Name") as cur:
                for row in cur:
                    names.append(row[0])
            parameters[1].filter.list = names

            if parameters[1].altered and not parameters[1].hasBeenValidated:
                # Check for required mosaic dataset fields
                missing_flds = []
                fld_list = [fld.name for fld in arcpy.ListFields(parameters[0].value)]
                for fld in self.mo_flds:
                    if fld not in fld_list:
                        missing_flds.append(fld)
                # If any fields are missing, show them in an error message
                if missing_flds:
                    parameters[0].setErrorMessage("Missing fields {} in {}".format(missing_flds, parameters[0].valueAsText))
                    return

                # clear the params
                parameters[2].value = None
                parameters[3].value = None
                parameters[4].value = None
                parameters[5].value = None
                parameters[6].value = None
                parameters[7].value = None


                # Get Layer Title and Mosaic Layer Data values for user-selected Mosaic Layer (param 1)
                if parameters[1].value:
                    where = "Name = '" + parameters[1].valueAsText + "'"
                    ##["Title", "Description", "Url", "Metadata", "NoDataRanges", "NoDataRangeLabels"]
                    with arcpy.da.SearchCursor(parameters[0].value, self.mo_flds, where) as cur:
                        row = cur.next()
##                        self._title = row[0]
##                        self._description = row[1]
##                        self._url = row[2]
##                        self._metadata = row[3]
##                        self._no_data_ranges = row[4]
##                        self._no_data_range_labels = row[5]

                        if row[0]:
                            parameters[2].value = row[0]
                        if row[1]:
                            parameters[3].value = row[1]
                        if row[2]:
                            parameters[4].value = row[2]
                        if row[3]:
                            parameters[5].value = row[3]
                        if row[4]:
                            try:
                                   parameters[6].value = row[4].split(",")[0]
                            except:
                                   parameters[6].value = None
                        if row[5]:
                            parameters[7].value = row[5]

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        # Check urls
        if parameters[4].value:
            if not parameters[4].valueAsText.lower().startswith("http://") and not parameters[4].valueAsText.lower().startswith("https://"):
                parameters[4].setErrorMessage("Url must begin with http:// or https://")

        if parameters[5].value:
            if not parameters[5].valueAsText.lower().startswith("http://") and not parameters[5].valueAsText.lower().startswith("https://"):
                parameters[5].setErrorMessage("Url must begin with http:// or https://")

        if parameters[6].value and (not isinstance(parameters[6].value, float)):
            parameters[6].setErrorMessage("NoData Value must be a number.")

        return


    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Read parameters from UI
        mosaic_dataset = parameters[0].value
        name = parameters[1].valueAsText
        title = parameters[2].valueAsText
        description = parameters[3].valueAsText
        url = parameters[4].valueAsText
        metadata = parameters[5].valueAsText
        #no_data_ranges = parameters[6].valueAsText
        if parameters[6].value:
             no_data_ranges = str(parameters[6].valueAsText) + "," + str(parameters[6].valueAsText)
        else:
             no_data_ranges = None
        no_data_range_labels = parameters[7].valueAsText

        # Where clause
        where = "Name = '" + name + "'"

        # Check for user changes
        changes = False
        ##["Title", "Description", "Url", "Metadata", "NoDataRanges", "NoDataRangeLabels"]
        with arcpy.da.SearchCursor(mosaic_dataset, self.mo_flds, where) as cur:
            row = cur.next()
            if title != row[0]:
                changes = True
                arcpy.AddMessage("Title:")
                arcpy.AddMessage("\tOriginal: " + row[0])
                arcpy.AddMessage("\tNew: " + title)
            if description != row[1]:
                changes = True
                arcpy.AddMessage("Description:")
                self.showMessages(row[1],description)
            if url != row[2]:
                changes = True
                arcpy.AddMessage("Url:")
                self.showMessages(row[2],url)
            if metadata != row[3]:
                changes = True
                arcpy.AddMessage("Metadata:")
##                arcpy.AddMessage("\tOriginal: " + row[3])
##                arcpy.AddMessage("\tNew: " + metadata)
                self.showMessages(row[3],metadata)
            if no_data_ranges != row[4]:
                changes = True
                arcpy.AddMessage("NoDataValue:")
##                arcpy.AddMessage("\tOriginal: " + row[4])
##                arcpy.AddMessage("\tNew: " + no_data_ranges)
                self.showMessages(row[4],no_data_ranges)
            if no_data_range_labels != row[5]:
                changes = True
                arcpy.AddMessage("NoDataLabel:")
##                arcpy.AddMessage("\tOriginal: " + row[5])
##                arcpy.AddMessage("\tNew: " + no_data_range_labels)
                self.showMessages(row[5],no_data_range_labels)

        # Update Mosaic Dataset table with values from tool UI
        if changes:
            if title == "":
                title = None
            if description == "":
                description = None
            if url == "":
                url = None
            if metadata == "":
                url = None
            if no_data_ranges == "":
                no_data_ranges = None
            if no_data_range_labels == "":
                no_data_range_labels = None

            # Update record with user-defined values
            ##["Title", "Description", "Url", "Metadata", "NoDataRanges", "NoDataRangeLabels"]
            with arcpy.da.UpdateCursor(mosaic_dataset, self.mo_flds, where) as cur:
                for row in cur:
                    row = (title, description, url, metadata, no_data_ranges, no_data_range_labels)
                    cur.updateRow(row)
        else:
            arcpy.AddMessage("No changes found")

        return

    def showMessages(this,rowByIdx,paramTitle):
        if rowByIdx is None:
            arcpy.AddMessage("\tOriginal: Empty")
        else:
            arcpy.AddMessage("\tOriginal: " + rowByIdx)

        if paramTitle is None:
            arcpy.AddMessage("\tNew: Empty")
        else:
            arcpy.AddMessage("\tNew: " + paramTitle)

        return


class CreateWeightedOverlayMosaic(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Weighted Overlay Mosaic"
        self.description = "Creates a new mosaic dataset that you can use to share as a weighted raster overlay service on ArcGIS Online or your portal."
        self.description += "The output mosaic dataset contains the raster layers in the input map document."
        self.canRunInBackground = False
        self.inTableSchema=["title","rasterPath","Label","minRangeValue","maxRangeValue","SuitabilityVal","Description","NoDataVal","NoDataLabel","URL"]
        self.outMoFields=[('Title','String',50),('Description','String',1024),('Url','String',1024),('InputRanges','String',256),('NoDataRanges','String',256),('RangeLabels','String',1024),('NoDataRangeLabels','String',1024),('OutputValues','String',256),('Metadata','String',1024),('dataset_id','String',50)]
        self.updMoFields=["Title","RangeLabels","InputRanges","OutputValues"]
        self.updMoFieldsQuery=["Name"]
        self.rasterType='Raster Dataset'
        self.resampling='NEAREST'

    def getParameterInfo(self):
        """Define parameter definitions"""

        in_workspace = arcpy.Parameter(
        displayName="Output Geodatabase",
        name="in_workspace",
        datatype="DEWorkspace",
        parameterType="Required",
        direction="Input")

        # set a default workspace
        in_workspace.value=arcpy.env.workspace

        in_mosaicdataset_name = arcpy.Parameter(
        displayName="Mosaic Dataset Name",
        name="in_mosaicdataset_name",
        datatype="GPString",
        parameterType="Required",
        direction="Input")

        arcpy.env.outputCoordinateSystem = arcpy.SpatialReference(3857)

        outMosaic=arcpy.Parameter(
        displayName="Output Mosaic Dataset",
        name="outMosaic",
        datatype="DEMosaicDataset",
        parameterType="Derived",
        direction="Output")

        params = [in_workspace,in_mosaicdataset_name,outMosaic]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        # should check for advanced as this requires frequency tool
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        try:
            if (parameters[0].value):
                desc = arcpy.Describe(parameters[0].valueAsText)
                if desc.workspaceType != 'LocalDatabase':
                    parameters[0].setErrorMessage("Invalid workspace type: Use only file geodatabases for output workspace")
                    return

            if (parameters[1].value):
                if (str(parameters[0].value) != None or str(parameters[0]) != "#"):
                    mdPath = os.path.join(parameters[0].valueAsText,parameters[1].valueAsText)
                    if arcpy.Exists(mdPath):
                        parameters[1].setWarningMessage(parameters[1].valueAsText + ": Existing dataset will be overwritten.")

                # Show error if invalid characters are in mosiac dataset name.
                chars = set(" ~`!@#$%^&*(){}[]-+=<>,.?|")
                datasetName = str(parameters[1].value)
                if any((c in chars) for c in datasetName):
                    parameters[1].setErrorMessage("Invalid mosaic dataset name.")
                    return

        except Exception as e1:
            parameters[0].setErrorMessage(this.GetErrorMessage(e1))
            return

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        # validate the layers
        p=arcpy.mp.ArcGISProject("CURRENT")
        m=p.listMaps("*")[0]
        lyrs=m.listLayers()
        lyrCheck=[]
        lyrPaths=[]
        for l in lyrs:
            # describe the layer to see if it's a raster, mosaice, etc
            d=arcpy.Describe(l)
            if hasattr(d,'datasetType'):
                if d.datasetType=="MosaicDataset":
                    arcpy.AddError("Cannot process mosaic dataset {}".format(l.name))
                    arcpy.AddError("Please remove mosaic dataset {} from the contents pane".format(l.name))
                    return

            if l.isRasterLayer:
                if l.name in lyrCheck:
                    arcpy.AddError("This map contains duplicate raster layer names. Use uniquely named layers.")
                    return
                else:
                    lyrCheck.append(l.name)
                    if l.supports("DATASOURCE"):
                        lyrPaths.append(l.dataSource)


        outMosaic=""
        workspace=""
        rasterPaths=[]

        try:

            # if there's no workspace set in param0, set it to the default workspace
            if (str(parameters[0].value) == None or str(parameters[0]) == "#"):
                arcpy.AddWarning("Setting workspace to {}".format(arcpy.env.workspace))
                workspace=arcpy.env.workspace
            else:
                workspace=parameters[0].valueAsText

            # make sure the workspace exists
            if arcpy.Exists(workspace)==False:
                arcpy.AddError("Workspace {} does not exist".format(workspace))
                return

            # describe the workspace to make sure it's an fGdb
            desc = arcpy.Describe(workspace)
            if desc.workspaceType != 'LocalDatabase':
                arcpy.AddError("Invalid workspace type: {}".format(workspace))
                return

            # if there's no output mosaic name (param1), exit
            if (str(parameters[1].value) == None or str(parameters[1]) == "#"):
                arcpy.AddError("Missing output mosaic name")
                return
            else:
                mosaicName=parameters[1].valueAsText

            # Create layer data that contains input ranges, output values, and range labels
            lyrData = self.AddWeightedOverlayRemapValues(lyrs)
            if lyrData == False:
                return

            # Create a mosaic path from param1 and 2
            outMosaic = os.path.join(workspace,mosaicName)

            # remove if it exists
            if arcpy.Exists(outMosaic):
                arcpy.Delete_management(outMosaic)
                arcpy.AddMessage(arcpy.GetMessages())

            arcpy.AddMessage("Creating mosaic...")

            # web mercator for all mosaics
            spatialref=arcpy.SpatialReference(3857)

            # Create the mosaic and get its output (for the output param)
            arcpy.AddMessage("Creating the mosaic dataset")
            res = arcpy.CreateMosaicDataset_management(workspace,mosaicName,spatialref,'#', '#', 'NONE', '#')

        except Exception as e2:
            arcpy.AddError("Error creating the mosaic {}:{} ".format(outMosaic,self.GetErrorMessage(e2)))
            return

        try:
            # create additional fields for the mosaic
            arcpy.AddMessage("Adding weighted overlay fields to the mosaic dataset...")
            for fldDef in self.outMoFields:
                fname=fldDef[0]
                ftype=fldDef[1]
                flength=fldDef[2]

                arcpy.AddField_management(outMosaic,fname,ftype,field_length=flength)
                arcpy.AddMessage(arcpy.GetMessages())

        except Exception as e3:
            arcpy.AddError("Error adding fields to the mosaic {}: ".format(outMosaic,self.GetErrorMessage(e3)))
            return


        try:
            #Change the Mosaic resampling type to Nearest Neighbor
            arcpy.AddMessage("Setting resampling type...")
            res = arcpy.SetMosaicDatasetProperties_management(res, resampling_type='NEAREST')
            arcpy.AddMessage(arcpy.GetMessages())

        except Exception as e_resampling:
            arcpy.AddError("Error setting resampling type {}: ".format(outMosaic,self.GetErrorMessage(e_resampling)))
            return


        try:
            # add rasters from the map document to the mosaic
            arcpy.AddMessage("Adding rasters to the mosaic")

            # for each layer in lyrPaths -
            #  1. verify there's layer data
            #  2. append the layer and to a list
            for lyr in lyrPaths:
                # check for the layer data in list
                if not any(name[0] == (os.path.splitext(os.path.basename(lyr))[0]) for name in lyrData):
                    arcpy.AddWarning("{} is missing layer data.".format(lyr))
                    arcpy.AddWarning("{} will not be inserted into the mosaic".format(lyr))
                rasterPaths.append(lyr)
            if len(rasterPaths) > 0:
                arcpy.AddRastersToMosaicDataset_management(outMosaic,self.rasterType,rasterPaths)
                arcpy.AddMessage(arcpy.GetMessages())
            else:
                arcpy.AddError("No layers in this map document have layer data. Please run tool Add Weighted Overlay Data to create these files.")
                return

        except Exception as e7:
            arcpy.AddError("Error adding rasters to the mosaic {}: ".format(self.GetErrorMessage(e7)))
            return

        try:
            # loop through layer data list
            arcpy.AddMessage("Updating mosaic with data from layer...")
            for item in lyrData:
                # Read data from each layer file
                title=item[0]
                inputranges=item[1]
                outputVals=item[2]
                labels=item[3]
                rasterFileName=item[4]

                # create a where clause from rasterfilename
                where="{}='{}'".format(self.updMoFieldsQuery[0],rasterFileName)

                # update the mosaic with data from the lyrData list
                # self.updMoFields = ["Title","RangeLabels","InputRanges","OutputValues"]
                with arcpy.da.UpdateCursor(outMosaic,self.updMoFields,where) as cursor:
                    for row in cursor:
                        row[0]=title
                        row[1]=labels
                        row[2]=inputranges
                        row[3]=outputVals
                        cursor.updateRow(row)


            arcpy.SetParameter(2,outMosaic)

        except Exception as e4:
            arcpy.AddError("Error adding data to the mosaic {}: ".format(mosaicFullPath,self.GetErrorMessage(e4)))
            return

        return

    def makeInputRanges(this,sourceRaster):
        # Creates input ranges from classified colorizers (or no colorizers)
        res=arcpy.GetRasterProperties_management(sourceRaster,"MINIMUM")
        minVal=float(str(res.getOutput(0)))
        res=arcpy.GetRasterProperties_management(sourceRaster,"MAXIMUM")
        maxVal=float(str(res.getOutput(0)))

        # Create an equal interval array of values
        sourceValues=np.linspace(minVal,maxVal,6,endpoint=True)

        inputRangesForRemap=""

        # Array must have 6 items
        if len(sourceValues) != 6:
            arcpy.AddWarning("Could not compute equal intervals in Raster {}".format(sourceRaster))
            return False, inputRangesForRemap

        # Check if all items in the array are the same
        if (sourceValues[0] == sourceValues[1] == sourceValues[2] == sourceValues[3]
            == sourceValues[4] == sourceValues[5]):
            ## all items in the array are the same!
            arcpy.AddWarning("Raster {} has same min and max value".format(sourceRaster))

            # create the max exclusive value
            maxVal=float(sourceValues[5])
            maxVal+=1

            # Create a single pair range
            inputRangesForRemap+="{},{}".format(sourceValues[4],maxVal) #has only 1 pair

            arcpy.AddWarning("Range for raster {} is {}".format(sourceRaster, inputRangesForRemap))
            arcpy.AddMessage(arcpy.GetMessages())


        else:
            #format into pairs of min-inclusive/max exclusive
            inputRangesForRemap+="{},{}".format(sourceValues[0],sourceValues[1]) #pair 1
            inputRangesForRemap+=",{},{}".format(sourceValues[1],sourceValues[2]) #pair 2
            inputRangesForRemap+=",{},{}".format(sourceValues[2],sourceValues[3]) #pair 3
            inputRangesForRemap+=",{},{}".format(sourceValues[3],sourceValues[4]) #pair 4
            maxVal=float(sourceValues[5])
            maxVal+=1
            inputRangesForRemap+=",{},{}".format(sourceValues[4],maxVal) #pair 5

        return True, inputRangesForRemap

    # creates input ranges from unique value colorizer
    def makeDataFromUniqueColorizer(this,rsDataset,symb):
        uvLabels=""
        uvRngs=""
        inRngs1=[]
        inRngs2=[]
        outVals=""

        # If the colorizer symbolizes on a field other than Value:
        # Fetch the Values from the raster's attribute table
        # and match them to the values and labels in the colorizer
        if symb.colorizer.field != 'Value':
            # Create a list of list that contains values and labels
            vals=[]
            for grp in symb.colorizer.groups:
                for itm in grp.items:
                    vals.append([itm.values[0],itm.label])

            arcpy.AddMessage("Colorizer values and labels {}".format(vals))
            arcpy.GetMessages()

            # check for a value field
            d=arcpy.Describe(rsDataset)
            foundValue=False
            for f in d.fields:
                if f.name.lower()=="value": foundValue=True

            if foundValue==False:
                arcpy.AddWarning("Raster {} has no value field".format(rsDataset))
                return False

            # get values and the colorizer field from the raster into a list of lists
            fields=["Value",symb.colorizer.field]
            rasterVals=[]
            with arcpy.da.SearchCursor(rsDataset, fields) as cursor:
                for row in cursor:
                    rasterVals.append([row[0],row[1]])


            # these two lists should be the same size
            if len(rasterVals) != len(vals):
                arcpy.AddWarning("Could not determine raster values and raster colorizer values")
                arcpy.GetMessages()
                return False, "",[], ""

            # iterate through rasterValues and reach into vals to build a list of input ranges, outVals and uvLabels
            for rasterValue in rasterVals:
                # format input ranges
                inRngs1.append(float(rasterValue[0]))
                inRngs2.append(float(rasterValue[0]))

                # rasterValue[1] is the row value (the symb.colorizer.field)
                for colorizerValue in vals:
                    if rasterValue[1].lower()==colorizerValue[0].lower():
                        # use the colorizerValue[1] (the label from the sym.colorizer) as our uvLabel
                        if len(uvLabels) < 1:
                            uvLabels='{}'.format(colorizerValue[1])
                        else:
                            uvLabels+=',{}'.format(colorizerValue[1])

                # create a comma-delimited list of output values
                # for now, all output values are set to 5
                if len(outVals)<1:
                    outVals='5'
                else:
                    outVals+=',5'


            worked, uvRngs = this.createInputRangesForRemap(inRngs1,inRngs2)

        else:
            # Colorizer symbolizes on Value field
            for grp in symb.colorizer.groups:
                for itm in grp.items:
                    # Create a comma-delimited list of labels
                    if len(uvLabels) < 1:
                        uvLabels='{}'.format(itm.label)
                    else:
                        uvLabels+=',{}'.format(itm.label)

                    # build two lists of unique values
                    v1=itm.values[0]
                    inRngs1.append(float(v1))
                    v2=itm.values[0]
                    inRngs2.append(float(v2))

                    # create a comma-delimited list of output values
                    # for now, all output values are set to 5
                    if len(outVals)<1:
                        outVals='5'
                    else:
                        outVals+=',5'

            worked, uvRngs = this.createInputRangesForRemap(inRngs1,inRngs2)


        return True, uvRngs, outVals, uvLabels

    ## Returns a comma delimited string that represents min-inclusive, max-exclusive ranges
    ## for the remap function
    def createInputRangesForRemap(this,rangeList1,rangeList2):
        # combine the two range lists
        combinedRngs=rangeList1+rangeList2

        # sort, the remove the 1st and change the last items, and finally convert it to strings
        # do this to create a list of min-inclusive,max-exlusive values for the raster remap function
        combinedRngs.sort()
        combinedRngs.remove(combinedRngs[0])
        lastValue=combinedRngs[-1]
        lastValue+=1
        combinedRngs.append(lastValue)
        thematicRange=','.join(str(x) for x in combinedRngs)

        return True, thematicRange


    def AddWeightedOverlayRemapValues(this,mLyrs):
        try:
            if (mLyrs):
                rasterLayers=[]
                lyrCheck=[]
                lyrData =[]

                # check for raster layers
                for l in mLyrs:
                    if (l.isRasterLayer):
                        if l.name in lyrCheck:
                            arcpy.AddError("This document contains duplicate raster layer names. Use uniquely named layers.")
                            return False
                        else:
                            lyrCheck.append(l.name)
                            rasterLayers.append(l)

                    else:
                        arcpy.AddWarning("Cannot process layer {}. Not a raster layer".format(l.name))

                # exit if there are none
                if len(rasterLayers)<1:
                    arcpy.AddError("There are no raster layers to process in this document")
                    return False
                else:
                    arcpy.AddMessage("Processing {} raster layers".format(len(rasterLayers)))

                rastertitle=""
                rasterpath=""
                rasterExtension=""
                outputValues=""
                labels=""
                rasterFileName = ""
                inras=""
                #inaux=""
                rasData=[]

                # Process Unique values and stretch/classified colorizers
                for l in rasterLayers:
                    try:
                        arcpy.AddMessage("Processing layer {}...".format(l.name))
                        rastertitle=l.name
                        # Create another variable that represents the toc layer name
                        rasterpath=l.dataSource
                        #layerDesc=l.description
                        rasterExtension="" # clear any values set

                        # Define raster file name from folder path
                        counter = rasterpath.rfind("\\") +1
                        rasterFileName = rasterpath[counter:len(rasterpath)]

                        # describe the raster to get its no data values & other info
                        desc=arcpy.Describe(l)
                        inras=desc.catalogPath


                        # check for an extension in the name (like foo.tif)
                        try:
                            rasterExtension=desc.extension

                            # remove it from the title
                            rastertitle=rastertitle.replace(rasterExtension,"")
                            if rastertitle.endswith("."):
                                rastertitle=rastertitle.replace(".","")
                            arcpy.AddWarning("Removed extension {} from layer {}".format(rasterExtension,rastertitle))

                            # remove it from file name
                            rasterFileName = rasterFileName.replace(rasterExtension, "")
                            if rasterFileName.endswith("."):
                                rasterFileName=rasterFileName.replace(".","")


                        except Exception as eExt:
                            arcpy.AddError("Extension error {}".format(this.GetErrorMessage(eExt)))
                            pass


                        # Process unique values differently than stretch/classified
                        sym=l.symbology

                        # string that represents min inclusive/max exclusive values
                        inputRanges=""

                        # http://pro.arcgis.com/en/pro-app/tool-reference/data-management/get-raster-properties.htm
                        # Process GENERIC, ELEVATION, PROCESSED AND SCIENTIFIC rasters by computing an equal interval classification
                        # Process THEMATIC rasters as unique values/categorical
                        rasterSourcetypeResult = arcpy.GetRasterProperties_management(inras, "SOURCETYPE")
                        rasterSourcetype = rasterSourcetypeResult.getOutput(0)
                        arcpy.AddMessage("{} is {}".format(inras, rasterSourcetype))

                        if rasterSourcetype.upper() == "THEMATIC" or (hasattr(sym,'colorizer') and sym.colorizer.type=='RasterUniqueValueColorizer'):
                            worked, inputRanges, outputValues, labels = this.makeDataFromUniqueColorizer(inras,sym)
                            if worked==False:
                                arcpy.AddWarning("Could not create ranges for unique colorizer in {}".format(inras))
                                arcpy.AddMessage(arcpy.GetMessages())
                                continue

                        elif rasterSourcetype.upper() == "VECTOR_UV" or rasterSourcetype.upper() == "VECTOR_MAGDIR":
                            arcpy.AddWarning("Skipping data type of VECTOR_UV or VECTOR_MAGDIR {}".format(inras))
                            arcpy.AddMessage(arcpy.GetMessages())
                            continue

                        else:
                            # no colorizer, try to the min-max values anyways
                            # check min and max values in the dataset
                            try:
                                worked, inputRanges = this.makeInputRanges(inras)
                            except Exception as e_inputRanges:
                                arcpy.AddWarning("Error creating input ranges for layer {}: {}".format(rastertitle, this.GetErrorMessage(e_inputRanges)))
                                continue

                            if worked==False:
                                arcpy.AddWarning("Could not create ranges for {}".format(inras))
                                arcpy.AddMessage(arcpy.GetMessages())
                                continue

                            else:
                                # set outputValues and Range Labels
                                outputValues="1,3,5,7,9"
                                labels="Very Low, Low, Medium, High, Very High"

                        rasData=(rastertitle,inputRanges,outputValues,labels,rasterFileName)
                        lyrData.append(rasData)
                        arcpy.AddMessage("input ranges: {}".format(inputRanges))
                        arcpy.AddMessage(arcpy.GetMessages())

                    except Exception as e1:
                        arcpy.AddError("Exception occurred: {}".format(this.GetErrorMessage(e1)))
                        return False
            else:
                arcpy.AddError("Invalid ArcGIS Project: {}".format(aMapdoc))
                return False

            return lyrData

        except Exception as e:
            arcpy.AddError("Exception occurred: {}".format(this.GetErrorMessage(e)))
            return False

    # Get exception message if available, otherwise use exception.
    def GetErrorMessage(this, e):
        if hasattr(e, 'message'):
            return e.message
        else:
            return e
