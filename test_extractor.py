from datasheet_extractor import DatasheetExtractor

def test_basic_extraction():
    # Create an instance of DatasheetExtractor
    extractor = DatasheetExtractor()
    
    # Test sample text
    sample_text = """
    ATmega328P Microcontroller
    
    Type: Microcontroller
    Part Number: ATmega328P
    Package: PDIP-28
    Pins: 28
    
    Operating Voltage: 1.8V to 5.5V
    Maximum Current: 200mA
    Operating Temperature: -40°C to 85°C
    
    Pin Configuration:
    Pin 1: RESET
    Pin 7: VCC
    Pin 8: GND
    Pin 9: Crystal1
    Pin 10: Crystal2
    """
    
    # Process the sample text
    result = extractor.process_datasheet(sample_text)
    
    # Print results
    print("\nExtracted Parameters:")
    print("-" * 20)
    for key, value in result['parameters'].items():
        print(f"{key}: {value}")
    
    print("\nPin Connections:")
    print("-" * 20)
    for pin in result['connections']['all_pins']:
        print(f"Pin {pin['number']}: {pin.get('description', '')}")

if __name__ == "__main__":
    test_basic_extraction() 