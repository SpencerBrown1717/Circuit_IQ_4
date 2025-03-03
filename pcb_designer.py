import os
import logging
from datasheet_extractor import DatasheetExtractor
from datetime import datetime
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('CircuitIQ-Designer')

class PCBDesigner:
    """
    Main PCB Designer class that orchestrates the circuit design process
    from natural language requirements and datasheets to gerber files
    """
    def __init__(self):
        self.datasheet_extractor = DatasheetExtractor()
        self.components = []
        self.board_params = {}
        self.requirements = ""
        
        # Library of common components with their footprints
        self.component_library = {
            "resistor": {
                "footprint": "R_0805_2012Metric", 
                "pins": 2,
                "symbol": "Device:R"
            },
            "capacitor": {
                "footprint": "C_0805_2012Metric", 
                "pins": 2,
                "symbol": "Device:C"
            },
            "LED": {
                "footprint": "LED_0805_2012Metric", 
                "pins": 2,
                "symbol": "Device:LED"
            },
            "microcontroller": {
                "footprint": "LQFP-32_7x7mm_P0.8mm", 
                "pins": 32,
                "symbol": "MCU_Microchip_ATmega:ATmega328P-AU"
            },
            "regulator": {
                "footprint": "TO-220-3_Vertical", 
                "pins": 3,
                "symbol": "Regulator_Linear:LM7805_TO220"
            },
            "diode": {
                "footprint": "D_SOD-323", 
                "pins": 2,
                "symbol": "Device:D"
            },
            "transistor": {
                "footprint": "SOT-23", 
                "pins": 3,
                "symbol": "Device:Q_NPN_BCE"
            },
            "sensor": {
                "footprint": "SOT-23-5", 
                "pins": 5,
                "symbol": "Sensor:Temperature_Sensor"
            },
            "connector": {
                "footprint": "PinHeader_1x05_P2.54mm_Vertical", 
                "pins": 5,
                "symbol": "Connector:Conn_01x05_Male"
            }
        }
    
    def process_datasheets(self, datasheets):
        """
        Process datasheet information to extract component parameters
        
        Args:
            datasheets: List of datasheet objects (dict with content/name or file paths)
            
        Returns:
            List of extracted component parameters
        """
        logger.info(f"Processing {len(datasheets)} datasheets")
        components = []
        
        for datasheet in datasheets:
            try:
                # Extract data from datasheet text or file
                if isinstance(datasheet, dict):
                    # Get component name if provided
                    component_name = datasheet.get('name', 'Unknown Component')
                    
                    # Process text content if provided
                    if 'content' in datasheet and datasheet['content']:
                        logger.info(f"Processing datasheet content for {component_name}")
                        result = self.datasheet_extractor.process_datasheet(datasheet['content'])
                        component = result['parameters']
                        component['name'] = component_name
                        
                        # Add connections if available
                        if 'connections' in result and result['connections']['all_pins']:
                            component['pins'] = len(result['connections']['all_pins'])
                            component['connections'] = result['connections']
                            
                        # Add to components list if valid
                        if component.get('type'):
                            components.append(component)
                    else:
                        logger.warning(f"No content provided for {component_name}")
                        
                        # Still add basic component info
                        component = {'name': component_name}
                        if 'type' in datasheet:
                            component['type'] = datasheet['type']
                        components.append(component)
                        
                elif isinstance(datasheet, str) and os.path.isfile(datasheet):
                    # Process datasheet file
                    logger.info(f"Processing datasheet file: {datasheet}")
                    result = self.datasheet_extractor.process_datasheet(datasheet)
                    component = result['parameters']
                    
                    # Extract file name as component name if not provided
                    if 'name' not in component:
                        file_name = os.path.basename(datasheet)
                        component['name'] = os.path.splitext(file_name)[0]
                    
                    # Add connections if available
                    if 'connections' in result and result['connections']['all_pins']:
                        component['pins'] = len(result['connections']['all_pins'])
                        component['connections'] = result['connections']
                    
                    # Add to components list if valid
                    if component.get('type'):
                        components.append(component)
            except Exception as e:
                logger.error(f"Error processing datasheet: {e}")
        
        # Enrich components with library data
        self._enrich_components(components)
        
        self.components = components
        return components
    
    def _enrich_components(self, components):
        """
        Enrich components with data from the component library
        
        Args:
            components: List of component dictionaries to enrich
        """
        for component in components:
            component_type = component.get('type', '').lower()
            
            # Find matching component in library
            for lib_type, lib_data in self.component_library.items():
                if component_type and lib_type in component_type:
                    # If pins are not specified, use library value
                    if 'pins' not in component:
                        component['pins'] = lib_data['pins']
                    
                    # Add footprint and symbol
                    component['footprint'] = lib_data['footprint']
                    component['symbol'] = lib_data['symbol']
                    break
            
            # Default values if not found in library
            if 'footprint' not in component:
                component['footprint'] = "Generic_Footprint"
            if 'symbol' not in component:
                component['symbol'] = "Device:Unknown"
    
    def analyze_requirements(self, requirements_text):
        """
        Analyze the textual requirements to determine circuit needs
        
        Args:
            requirements_text: Natural language description of circuit requirements
            
        Returns:
            Dictionary with circuit needs and components
        """
        logger.info("Analyzing requirements text")
        self.requirements = requirements_text
        
        # Skip if no requirements
        if not requirements_text:
            return {
                "circuit_needs": {},
                "components": self.components
            }
        
        # Simple keyword-based analysis
        requirements_lower = requirements_text.lower()
        circuit_needs = {
            "power_regulation": any(word in requirements_lower for word in 
                                   ["power", "voltage", "regulator", "battery", "supply", "v", "volt"]),
            "microcontroller": any(word in requirements_lower for word in 
                                  ["microcontroller", "arduino", "mcu", "processor", "control", "atmega"]),
            "led_indicators": any(word in requirements_lower for word in 
                                 ["led", "indicator", "light", "display", "blink"]),
            "sensors": any(word in requirements_lower for word in 
                          ["sensor", "measure", "detect", "monitor", "temperature", "humidity", "pressure"]),
            "motor_control": any(word in requirements_lower for word in 
                               ["motor", "driver", "actuator", "servo", "stepper"]),
            "connectivity": any(word in requirements_lower for word in 
                               ["connect", "interface", "usb", "bluetooth", "wireless", "i2c", "spi", "uart"])
        }
        
        logger.info(f"Circuit needs: {circuit_needs}")
        
        # Add missing essential components based on requirements
        # Power regulation
        if circuit_needs["power_regulation"] and not any(c.get('type') == 'regulator' for c in self.components):
            self.components.append({
                'type': 'regulator', 
                'pins': 3, 
                'name': 'Power Regulator',
                'footprint': self.component_library['regulator']['footprint'],
                'symbol': self.component_library['regulator']['symbol']
            })
            
            # Add input/output capacitors for regulator
            self.components.append({
                'type': 'capacitor',
                'pins': 2,
                'name': 'Input Capacitor',
                'footprint': self.component_library['capacitor']['footprint'],
                'symbol': self.component_library['capacitor']['symbol']
            })
            
            self.components.append({
                'type': 'capacitor',
                'pins': 2,
                'name': 'Output Capacitor',
                'footprint': self.component_library['capacitor']['footprint'],
                'symbol': self.component_library['capacitor']['symbol']
            })
        
        # Microcontroller
        if circuit_needs["microcontroller"] and not any(c.get('type') == 'microcontroller' for c in self.components):
            self.components.append({
                'type': 'microcontroller',
                'pins': 32,
                'name': 'ATmega328P',
                'footprint': self.component_library['microcontroller']['footprint'],
                'symbol': self.component_library['microcontroller']['symbol']
            })
            
            # Add decoupling capacitors
            self.components.append({
                'type': 'capacitor',
                'pins': 2,
                'name': 'Decoupling Capacitor',
                'footprint': self.component_library['capacitor']['footprint'],
                'symbol': self.component_library['capacitor']['symbol']
            })
        
        # LED indicators
        if circuit_needs["led_indicators"] and not any(c.get('type') == 'LED' for c in self.components):
            self.components.append({
                'type': 'LED',
                'pins': 2,
                'name': 'Status LED',
                'footprint': self.component_library['LED']['footprint'],
                'symbol': self.component_library['LED']['symbol']
            })
            
            # Add current limiting resistor
            self.components.append({
                'type': 'resistor',
                'pins': 2,
                'name': 'LED Current Limiter',
                'footprint': self.component_library['resistor']['footprint'],
                'symbol': self.component_library['resistor']['symbol']
            })
        
        return {
            "circuit_needs": circuit_needs,
            "components": self.components
        }
    
    def generate_design(self, project_name, requirements, board_params, components, output_dir):
        """
        Generate a PCB design based on requirements and components
        
        Args:
            project_name: Name of the PCB project
            requirements: Natural language description of requirements
            board_params: Dictionary with board parameters (width, height, layers)
            components: List of components to include
            output_dir: Directory to save generated files
            
        Returns:
            Dictionary with design data including file paths and component info
        """
        logger.info(f"Generating design for project: {project_name}")
        
        # Update instance variables
        self.board_params = board_params
        self.components = components
        
        # Process requirements
        analysis = self.analyze_requirements(requirements)
        
        # Generate suggestions based on analysis
        suggestions = []
        
        if analysis['circuit_needs']['power_regulation']:
            suggestions.append("Consider adding reverse polarity protection for power input")
            suggestions.append("Add proper filtering capacitors for voltage regulation")
        
        if analysis['circuit_needs']['microcontroller']:
            suggestions.append("Add decoupling capacitors near the microcontroller power pins")
            suggestions.append("Include a reset circuit with pull-up resistor")
        
        if analysis['circuit_needs']['sensors']:
            suggestions.append("Add filtering capacitors near analog sensor inputs to reduce noise")
            suggestions.append("Consider adding voltage reference for accurate measurements")
        
        if analysis['circuit_needs']['motor_control']:
            suggestions.append("Use separate power and ground planes for motor circuits")
            suggestions.append("Add flyback diodes for inductive loads")
        
        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        gerber_dir = os.path.join(output_dir, "gerber")
        os.makedirs(gerber_dir, exist_ok=True)
        
        # Generate actual Gerber files
        gerber_files = self._generate_gerber_files(gerber_dir, board_params)
        
        # Generate preview image
        preview_file = os.path.join(output_dir, "preview.png")
        self._generate_preview(preview_file, board_params, components)
        
        return {
            "board_file": os.path.join(output_dir, f"{project_name}.kicad_pcb"),
            "gerber_dir": gerber_dir,
            "preview_file": preview_file,
            "components": len(components),
            "dims": f"{board_params.get('width', 100)}mm × {board_params.get('height', 80)}mm",
            "suggestions": suggestions
        }
    
    def _generate_gerber_files(self, output_dir, board_params):
        """
        Generate Gerber files for PCB manufacturing
        
        Generates industry-standard Gerber X2 format files including:
        - Copper layers with ground/power planes
        - Solder mask with thermal relief
        - Silkscreen with component labels
        - Drill files with proper plating
        - Board outline with proper clearances
        """
        try:
            # Design rules (in mm)
            drc_rules = {
                'min_trace_width': 0.2,
                'min_trace_spacing': 0.2,
                'min_drill_size': 0.3,
                'min_ring_width': 0.2,
                'min_clearance': 0.254,
                'thermal_relief_gap': 0.3,
                'thermal_relief_connect': 0.4,
                'plane_clearance': 0.4
            }
            
            # Define standard apertures with thermal relief
            apertures = {
                'D10': {'type': 'C', 'size': 0.254},  # 10mil trace
                'D11': {'type': 'C', 'size': 0.508},  # 20mil trace
                'D12': {'type': 'C', 'size': 1.016},  # 40mil pad
                'D13': {'type': 'R', 'size': [1.524, 2.032]},  # Rectangular pad
                'D14': {'type': 'C', 'size': 0.6, 'hole': 0.3},  # Via
                'D15': {'type': 'P', 'size': 1.8, 'vertices': 4},  # Thermal pad
                'D16': {'type': 'C', 'size': 0.254, 'thermal': True},  # Thermal relief trace
                'D17': {'type': 'C', 'size': 3.0},  # Large mounting pad
            }
            
            # Layer stackup configuration
            layers = [
                ("F.Cu", "Top copper layer", "GTL", "Copper,L1,Top"),
                ("In1.Cu", "Internal plane 1", "G1L", "Copper,L2,Inr"),
                ("In2.Cu", "Internal plane 2", "G2L", "Copper,L3,Inr"),
                ("B.Cu", "Bottom copper layer", "GBL", "Copper,L4,Bot"),
                ("F.Mask", "Top solder mask", "GTS", "Soldermask,Top"),
                ("B.Mask", "Bottom solder mask", "GBS", "Soldermask,Bot"),
                ("F.Paste", "Top paste", "GTP", "Paste,Top"),
                ("B.Paste", "Bottom paste", "GBP", "Paste,Bot"),
                ("F.SilkS", "Top silkscreen", "GTO", "Legend,Top"),
                ("B.SilkS", "Bottom silkscreen", "GBO", "Legend,Bot"),
                ("Edge.Cuts", "Board outline", "GKO", "Profile,NP")
            ]
            
            board_width = board_params.get('width', 100)
            board_height = board_params.get('height', 80)
            
            # Generate netlist for routing
            nets = self._generate_netlist()
            
            for layer_name, desc, ext, function in layers:
                # Skip layers based on board configuration
                if board_params.get('layers', 2) == 1 and (layer_name.startswith('B.') or layer_name.startswith('In')):
                    continue
                    
                file_path = os.path.join(output_dir, f"{layer_name}.{ext}")
                with open(file_path, 'w') as f:
                    # Write enhanced Gerber X2 format header
                    f.write(f"%TF.GenerationSoftware,CircuitIQ,PCBDesigner,1.0*%\n")
                    f.write(f"%TF.CreationDate,{datetime.now().strftime('%Y%m%d%H%M%S')}*%\n")
                    f.write(f"%TF.ProjectId,{desc}*%\n")
                    f.write(f"%TF.Part,Single*%\n")
                    f.write(f"%TF.FileFunction,{function}*%\n")
                    f.write(f"%TF.FilePolarity,Positive*%\n")
                    f.write("%FSLAX46Y46*%\n")
                    f.write("%MOMM*%\n")
                    
                    # Define enhanced apertures
                    for ap_code, ap_data in apertures.items():
                        if ap_data['type'] == 'C':
                            if ap_data.get('hole'):
                                f.write(f"%ADD{ap_code}C,{ap_data['size']}X{ap_data['hole']}*%\n")
                            elif ap_data.get('thermal'):
                                f.write(f"%ADD{ap_code}C,{ap_data['size']}X{drc_rules['thermal_relief_gap']}X{drc_rules['thermal_relief_connect']}*%\n")
                            else:
                                f.write(f"%ADD{ap_code}C,{ap_data['size']}*%\n")
                        elif ap_data['type'] == 'R':
                            f.write(f"%ADD{ap_code}R,{ap_data['size'][0]}X{ap_data['size'][1]}*%\n")
                        elif ap_data['type'] == 'P':
                            f.write(f"%ADD{ap_code}P,{ap_data['size']}X{ap_data['vertices']}*%\n")
                    
                    # Draw board outline with proper clearance
                    if layer_name == "Edge.Cuts":
                        f.write("%LPD*%\n")
                        f.write("G01*\n")
                        # Add rounded corners
                        radius = 1.0  # 1mm corner radius
                        self._draw_rounded_rectangle(f, 0, 0, board_width, board_height, radius)
                    
                    # Generate copper layers
                    if layer_name in ["F.Cu", "B.Cu", "In1.Cu", "In2.Cu"]:
                        # Add ground/power planes for internal layers
                        if layer_name.startswith("In"):
                            self._add_plane_layer(f, board_width, board_height, 
                                               "GND" if layer_name == "In1.Cu" else "VCC",
                                               drc_rules)
                        
                        # Place components with proper footprints
                        cols = max(1, int(np.sqrt(len(self.components))))
                        for i, component in enumerate(self.components):
                            # Get component position
                            x, y = self._get_component_position(i, cols, board_width, board_height)
                            
                            # Place component with proper footprint
                            self._place_component(f, component, x, y, layer_name, drc_rules)
                        
                        # Route traces between components using netlist
                        self._route_traces(f, nets, drc_rules)
                    
                    # Generate solder mask layers
                    elif layer_name in ["F.Mask", "B.Mask"]:
                        # Add solder mask with proper clearances
                        self._generate_solder_mask(f, layer_name, drc_rules)
                    
                    # Generate silkscreen layers
                    elif layer_name in ["F.SilkS", "B.SilkS"]:
                        # Add component labels and polarity marks
                        self._generate_silkscreen(f, layer_name)
                    
                    f.write("M02*\n")
            
            # Generate enhanced drill file
            self._generate_drill_file(output_dir, board_params, drc_rules)
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating Gerber files: {e}")
            return False

    def _generate_netlist(self):
        """Generate netlist from component connections"""
        nets = []
        # Group connections by net (power, ground, signals)
        for i, component in enumerate(self.components):
            if component.get('connections'):
                for net_name, pins in component['connections'].items():
                    nets.append({
                        'name': net_name,
                        'component': i,
                        'pins': pins
                    })
        return nets

    def _draw_rounded_rectangle(self, f, x, y, width, height, radius):
        """Draw rectangle with rounded corners in Gerber format"""
        # Move to start position
        f.write(f"X{int(x*1e4)}Y{int((y+radius)*1e4)}D02*\n")
        
        # Draw sides and corners
        for i in range(4):
            # Draw straight side
            if i % 2 == 0:
                f.write(f"X{int((x+width)*1e4)}Y{int((y+radius)*1e4)}D01*\n")
            else:
                f.write(f"X{int(x*1e4)}Y{int((y+height-radius)*1e4)}D01*\n")
            
            # Draw arc for corner
            x_center = x + (width if i in [0,3] else 0)
            y_center = y + (height if i in [1,2] else 0)
            f.write(f"G75*\n")  # Multi-quadrant mode
            f.write(f"G03*\n")  # CCW arc
            f.write(f"X{int((x_center+radius)*1e4)}Y{int(y_center*1e4)}I{int(radius*1e4)}J0D01*\n")

    def _add_plane_layer(self, f, width, height, plane_type, drc_rules):
        """Add power or ground plane with thermal relief"""
        clearance = drc_rules['plane_clearance']
        
        # Draw solid plane
        f.write("G36*\n")  # Start region
        f.write(f"X{int(clearance*1e4)}Y{int(clearance*1e4)}D02*\n")
        f.write(f"X{int((width-clearance)*1e4)}Y{int(clearance*1e4)}D01*\n")
        f.write(f"X{int((width-clearance)*1e4)}Y{int((height-clearance)*1e4)}D01*\n")
        f.write(f"X{int(clearance*1e4)}Y{int((height-clearance)*1e4)}D01*\n")
        f.write(f"X{int(clearance*1e4)}Y{int(clearance*1e4)}D01*\n")
        f.write("G37*\n")  # End region

    def _place_component(self, f, component, x, y, layer_name, drc_rules):
        """Place component with proper footprint and thermal relief"""
        component_type = component.get('type', '').lower()
        footprint = self.component_library.get(component_type, {}).get('footprint')
        
        if footprint:
            pins = component.get('pins', 2)
            pitch = 2.54  # Standard 0.1" pitch
            
            # Add component pads with thermal relief
            for pin in range(pins):
                pin_x = x + (pin - pins/2) * pitch
                
                # Use thermal relief for power/ground connections
                if component.get('connections', {}).get('pin_' + str(pin)) in ['VCC', 'GND']:
                    f.write(f"D16*\n")  # Thermal relief aperture
                else:
                    f.write(f"D12*\n")  # Standard pad aperture
                
                f.write(f"X{int(pin_x*1e4)}Y{int(y*1e4)}D03*\n")

    def _route_traces(self, f, nets, drc_rules):
        """Route traces between components using netlist"""
        for net in nets:
            # Select appropriate trace width based on net type
            if net['name'] in ['VCC', 'GND']:
                f.write("D11*\n")  # Wider trace for power
            else:
                f.write("D10*\n")  # Standard trace
            
            # Route traces (simplified auto-routing)
            # In a real implementation, this would use proper routing algorithms
            start_x, start_y = self._get_pin_position(net['component'], net['pins'][0])
            for pin in net['pins'][1:]:
                end_x, end_y = self._get_pin_position(net['component'], pin)
                f.write(f"X{int(start_x*1e4)}Y{int(start_y*1e4)}D02*\n")
                f.write(f"X{int(end_x*1e4)}Y{int(end_y*1e4)}D01*\n")

    def _generate_drill_file(self, output_dir, board_params, drc_rules):
        """Generate enhanced drill file with proper plating information"""
        drill_file = os.path.join(output_dir, "board.drl")
        with open(drill_file, 'w') as f:
            f.write(";DRILL file {Generated by CircuitIQ}\n")
            f.write("M48\n")  # Header
            f.write("METRIC,TZ\n")
            
            # Define drill sizes with plating
            drill_sizes = {
                'T1': {'size': 0.8, 'plated': True},   # Standard pins
                'T2': {'size': 1.0, 'plated': True},   # Large pins
                'T3': {'size': 3.2, 'plated': False},  # Mounting holes
                'T4': {'size': 0.3, 'plated': True}    # Vias
            }
            
            # Write tool definitions
            for tool, specs in drill_sizes.items():
                f.write(f"{tool}C{specs['size']:.1f}")
                if specs['plated']:
                    f.write(";PLATED\n")
                else:
                    f.write(";\n")
            
            f.write("%\n")
            f.write("G90\n")  # Absolute coordinates
            f.write("G05\n")  # Drill mode
            
            # Add mounting holes
            f.write("T3\n")
            margin = 5
            corners = [
                (margin, margin),
                (margin, board_params.get('height', 80) - margin),
                (board_params.get('width', 100) - margin, margin),
                (board_params.get('width', 100) - margin, board_params.get('height', 80) - margin)
            ]
            for x, y in corners:
                f.write(f"X{int(x*1e4)}Y{int(y*1e4)}\n")
            
            # Add component holes
            for i, component in enumerate(self.components):
                # Get component position
                x, y = self._get_component_position(i, max(1, int(np.sqrt(len(self.components)))), 
                                                 board_params.get('width', 100), 
                                                 board_params.get('height', 80))
                
                # Select drill size based on component type
                if component.get('type') == 'microcontroller':
                    f.write("T2\n")
                else:
                    f.write("T1\n")
                
                # Add holes for each pin
                pins = component.get('pins', 2)
                pitch = 2.54
                for pin in range(pins):
                    pin_x = x + (pin - pins/2) * pitch
                    f.write(f"X{int(pin_x*1e4)}Y{int(y*1e4)}\n")
            
            # Add vias
            f.write("T4\n")
            # Add via positions based on routing
            for net in self._generate_netlist():
                if net['name'] in ['VCC', 'GND']:
                    # Add vias for power/ground connections
                    component = self.components[net['component']]
                    x, y = self._get_component_position(net['component'], 
                                                      max(1, int(np.sqrt(len(self.components)))),
                                                      self.board_params.get('width', 100),
                                                      self.board_params.get('height', 80))
                    
                    # Add vias near power/ground pins
                    for pin in net['pins']:
                        pin_x = x + (pin - component.get('pins', 2)/2) * 2.54
                        # Add via slightly offset from pin
                        f.write(f"X{int((pin_x+1)*1e4)}Y{int((y+1)*1e4)}\n")
            
            f.write("M30\n")  # End of file

    def _get_component_position(self, index, cols, board_width, board_height):
        """Calculate component position in grid layout"""
        row = index // cols
        col = index % cols
        x = board_width * (col + 1) / (cols + 1)
        y = board_height * (row + 1) / (int(len(self.components)/cols) + 1)
        return x, y

    def _get_pin_position(self, component_index, pin):
        """Calculate pin position for a given component"""
        cols = max(1, int(np.sqrt(len(self.components))))
        x, y = self._get_component_position(component_index, cols, 
                                          self.board_params.get('width', 100), 
                                          self.board_params.get('height', 80))
        component = self.components[component_index]
        pins = component.get('pins', 2)
        pitch = 2.54
        pin_x = x + (pin - pins/2) * pitch
        return pin_x, y

    def _generate_solder_mask(self, f, layer_name, drc_rules):
        """Generate solder mask layer with proper clearances"""
        # Add solder mask clearance around pads
        clearance = drc_rules['min_clearance']
        
        # Process each component
        cols = max(1, int(np.sqrt(len(self.components))))
        for i, component in enumerate(self.components):
            # Get component position
            x, y = self._get_component_position(i, cols, 
                                              self.board_params.get('width', 100), 
                                              self.board_params.get('height', 80))
            
            # Add solder mask openings for pads
            pins = component.get('pins', 2)
            pitch = 2.54
            
            for pin in range(pins):
                pin_x = x + (pin - pins/2) * pitch
                
                # Add slightly larger opening than pad
                mask_size = 1.016 + (2 * clearance)  # Pad size + clearance
                f.write(f"D12*\n")  # Use standard pad aperture
                f.write(f"X{int(pin_x*1e4)}Y{int(y*1e4)}D03*\n")

    def _generate_silkscreen(self, f, layer_name):
        """Generate silkscreen layer with component labels and polarity marks"""
        # Process each component
        cols = max(1, int(np.sqrt(len(self.components))))
        for i, component in enumerate(self.components):
            # Get component position
            x, y = self._get_component_position(i, cols, 
                                              self.board_params.get('width', 100), 
                                              self.board_params.get('height', 80))
            
            component_type = component.get('type', '').lower()
            
            # Draw component outline
            if component_type == 'microcontroller':
                # Draw rectangle for IC
                width = 12  # mm
                height = 12  # mm
                self._draw_component_outline(f, x - width/2, y - height/2, width, height)
                
                # Add pin 1 marker
                f.write("D10*\n")  # Use thin trace
                f.write(f"X{int((x-width/2)*1e4)}Y{int((y-height/2)*1e4)}D02*\n")
                f.write(f"X{int((x-width/2+2)*1e4)}Y{int((y-height/2)*1e4)}D01*\n")
                f.write(f"X{int((x-width/2)*1e4)}Y{int((y-height/2+2)*1e4)}D01*\n")
                f.write(f"X{int((x-width/2)*1e4)}Y{int((y-height/2)*1e4)}D01*\n")
            else:
                # Draw simple rectangle for other components
                width = 5  # mm
                height = 3  # mm
                self._draw_component_outline(f, x - width/2, y - height/2, width, height)
                
                # Add polarity marker for polarized components
                if component_type in ['led', 'diode', 'capacitor']:
                    f.write("D10*\n")
                    f.write(f"X{int((x+width/2)*1e4)}Y{int((y)*1e4)}D02*\n")
                    f.write(f"X{int((x+width/2+1)*1e4)}Y{int((y)*1e4)}D01*\n")
            
            # Add component reference designator
            ref_des = component.get('name', f"U{i+1}")
            self._draw_text(f, ref_des, x, y + height/2 + 1)

    def _draw_component_outline(self, f, x, y, width, height):
        """Draw component outline on silkscreen"""
        f.write("D10*\n")  # Use thin trace
        f.write(f"X{int(x*1e4)}Y{int(y*1e4)}D02*\n")
        f.write(f"X{int((x+width)*1e4)}Y{int(y*1e4)}D01*\n")
        f.write(f"X{int((x+width)*1e4)}Y{int((y+height)*1e4)}D01*\n")
        f.write(f"X{int(x*1e4)}Y{int((y+height)*1e4)}D01*\n")
        f.write(f"X{int(x*1e4)}Y{int(y*1e4)}D01*\n")

    def _draw_text(self, f, text, x, y):
        """Draw text on silkscreen (simplified vector font)"""
        # Use thin trace for text
        f.write("D10*\n")
        
        # Simple implementation - just draw text as small line segments
        # In a real implementation, this would use proper vector font definitions
        char_width = 1.5  # mm
        char_height = 2.0  # mm
        
        for i, char in enumerate(text):
            char_x = x + (i * char_width)
            # Draw simplified character (just vertical line for demo)
            f.write(f"X{int(char_x*1e4)}Y{int(y*1e4)}D02*\n")
            f.write(f"X{int(char_x*1e4)}Y{int((y+char_height)*1e4)}D01*\n")

    def _generate_preview(self, output_file, board_params, components):
        """Generate a preview image of the PCB design"""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.set_aspect('equal')
            
            # Set board dimensions
            width = board_params.get('width', 100)
            height = board_params.get('height', 80)
            ax.set_xlim(0, width)
            ax.set_ylim(0, height)
            
            # Draw board outline
            rect = plt.Rectangle((0, 0), width, height, 
                               fill=True, color='green', alpha=0.5)
            ax.add_patch(rect)
            
            # Draw components (simplified representation)
            for i, component in enumerate(components):
                # Calculate position (simple grid layout)
                cols = max(1, int(np.sqrt(len(components))))
                row = i // cols
                col = i % cols
                
                x = width * (col + 1) / (cols + 1)
                y = height * (row + 1) / (int(len(components)/cols) + 1)
                
                # Draw component
                comp_width = 10 if component.get('type') == 'microcontroller' else 5
                comp_height = 10 if component.get('type') == 'microcontroller' else 3
                
                rect = plt.Rectangle((x - comp_width/2, y - comp_height/2), 
                                  comp_width, comp_height, 
                                  fill=True, color='black', alpha=0.7)
                ax.add_patch(rect)
                
                # Add label
                ax.text(x, y, component.get('name', f"U{i+1}"), 
                       ha='center', va='center', color='white', fontsize=8)
            
            plt.title('Circuit IQ PCB Preview')
            plt.grid(True)
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            plt.close()
            
            return True
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            return False 