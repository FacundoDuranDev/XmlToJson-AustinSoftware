import xml.etree.ElementTree as ET
import argparse
import json


class XmlToJson:
    def __init__(self):
        # namespaces used for the xml files
        self.namespaces = {
            "Flight1":  {
                "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
                "ns": "http://www.opentravel.org/OTA/2003/05/common/",
                    },
            "Flight2": {
                "": "http://www.iata.org/IATA/EDIST/2017.2"
                }
        }

        parser = argparse.ArgumentParser(description="Convert XML seatmaps into JSON")
        parser.add_argument(
                            'seatmap_file',
                            help="XML file to parse",
                            type=str,
                            default=None
                            )
        args = parser.parse_args()
        seatmap_file = args.seatmap_file

        if ".xml" not in seatmap_file:
            return "Error: The file is not an xml"
        
        
        try:
            dict_ = self.detect_type(seatmap_file)
        except ValueError as e:
            parser.error(str(e))
        if isinstance(dict_,dict):
            self.write_file(dict,seatmap_file)
    def detect_type(self,seatmap_file):
        """
        Detects the type of the seatmap file
        """
        try:
            root = ET.parse(seatmap_file).getroot()
            print("File accepted: " + seatmap_file)
            if root.tag.endswith('Envelope'):
                return self.flight_parse1(root)
            if root.tag.endswith('SeatAvailabilityRS'):
                return self.flight_parse2(root)
            raise ValueError("Unsupported XML Format")
                    # TODO: aditional validations
        except FileNotFoundError as error:
            print("The name of the file does not exist")

    def flight_parse1(self,root):
        flight = {}
        namespace = self.namespaces['Flight1']
        cabins = root.iterfind(
            (
            "soapenv:Body/ns:OTA_AirSeatMapRS/ns:SeatMapResponses/"
            "ns:SeatMapResponse/ns:SeatMapDetails/ns:CabinClass"
            ),
            namespace,
            )
        for cabin in cabins:
            for row in cabin:
                cabin_class = row.get('CabinType')
                seats = []
                for seat in row.iterfind('ns:SeatInfo', namespace):
                    summary = seat.find('ns:Summary', namespace)
                    service = seat.find('ns:Service', namespace)
                    if service:
                        fee = service.find('ns:Fee', namespace)
                        price = float(fee.get('Amount')) / 10 ** int(
                            fee.get('DecimalPlaces')
                        )
                        currency = fee.get('CurrencyCode')
                    else:
                        price = "no offer"
                        currency = price
                    seats.append(
                        {
                            "Id": summary.get('SeatNumber'),
                            "Available": summary.get('AvailableInd') == "true",
                            "CabinClass": cabin_class,
                            "Price": price,
                            "Currency": currency,
                            "SeatType": [
                                features.text
                                if "Other" not in features.text
                                else features.get('extension')
                                for features in seat.iterfind('ns:Features',namespace)
                            ]
                        }
                    )
                flight[row.get('RowNumber')] = seats
        return flight

    def flight_parse2(self,root):
        offers = {}
        namespace = self.namespaces['Flight2']
        for offer in root.iterfind(
            'ALaCarteOffer/ALaCarteOfferItem',
            namespace):
            currency_price = offer.find(
                'UnitPriceDetail/TotalAmount/SimpleCurrencyPrice',
                namespace
                )
            currency = currency_price.get('Code')
            price = float(currency_price.text)
            offers[offer.get('OfferItemID')] = currency, price
        defs = {
            defn.get(
                'SeatDefinitionID'
                ): defn.find(
                    'Description/Text',namespace
                    ).text
            for defn in root.iterfind(
                'DataLists/SeatDefinitionList/SeatDefinition',
                namespace
                )

        }
        flight = {}
        for row in root.iterfind(
            'SeatMap/Cabin/Row'
            ,namespace):
            seats = []
            row_num = row.find('Number', namespace).text
            for seat in row.iterfind('Seat',namespace):
                offer = seat.find('OfferItemRefs', namespace)
                if offer is not None:
                    price, currency = offers[offer.text]
                else:
                    price = "no offer"
                    currency = price
                seat_type = [
                defs[ref.text]
                for ref in seat.findall("SeatDefinitionRef", namespace)
                ]
                seats.append(
                    {
                        'Id': row_num + seat.find('Column', namespace).text,
                        "Available": "AVAILABLE" in seat_type,
                        "CabinClass": None,
                        "Price": price,
                        "Currency": currency,
                        "SeatType": [type for type in seat_type if type != "AVAILABLE"],

                    }
                )
            flight[row_num] = seats
        return flight

    def write_file(self,json_dict,filename):
        parsed_file_name = filename.split('.')[0] + "_parsed.json"
        with open(parsed_file_name, "w") as file:
            json.dump(json_dict, file)
        print("Your File was succesfully parsed")
        print("the name of the parsed file is " + parsed_file_name)


if __name__ == "__main__":
    XmlToJson()