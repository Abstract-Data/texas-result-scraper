from nameparser import HumanName
import re


def set_office_type(cls, values):
    OFFICE = values.get('office')
    if not OFFICE:
        OFFICE = values.get('name')
    if OFFICE:
        match OFFICE:
            # STATEWIDE
            case str(x) if "PRESIDENT" in x:
                values['office_type'] = "POTUS"
            case str(x) if "U. S. SENATOR" in x:
                values['office_type'] = "US Senate"
            case str(x) if "GOVERNOR" in x:
                values['office_type'] = "Governor"
            case str(x) if "STATE BOARD OF EDUCATION" in x:
                _values = OFFICE.split(",")
                values['office_type'] = "SBOE"
                values['office_district'] = _values[-1].strip()
            case "RAILROAD COMMISSIONER":
                values['office_type'] = "RRC"

            # JUDGES
            case str(x) if x.startswith("DISTRICT JUDGE"):
                values['office_type'] = "DISTRICT JUDGE"
                values['office_district'] = OFFICE.split(",")[-1].strip()
            case str(x) if x.startswith("JUSTICE") and "COURT OF APPEALS DISTRICT" in x:
                _values = OFFICE.split(",")
                values['office_type'] = _values[1].strip()
                values['office_district'] = _values[2].strip()
            case str(x) if x.startswith("JUSTICE") and "SUPREME COURT" in x:
                values['office_type'] = "SCOTX"
                values['office_district'] = OFFICE.split(",")[-1].strip()
            case str(x) if x.startswith("CRIMINAL DISTRICT JUDGE") and "COUNTY" in x:
                values['office_type'] = "CRIMINAL DISTRICT JUDGE"
                values['office_district'] = OFFICE.split(",")[-1].strip()
            case str(x) if x.startswith("CHIEF JUSTICE") and "COURT OF APPEALS DISTRICT" in x:
                _values = OFFICE.split(",")
                values['office_type'] = "CHIEF JUSTICE"
                values['office_district'] = _values[1].strip()
            case str(x) if x.startswith("JUDGE") and "COURT OF CRIMINAL APPEALS" in x:
                _values = OFFICE.split(",")
                values['office_type'] = _values[1].strip()
                values['office_district'] = _values[2].strip()
            case str(x) if x.startswith("PRESIDING JUDGE") and "COURT OF CRIMINAL APPEALS" in x:
                values['office_type'] = "PRESIDING JUDGE"
                values['office_district'] = OFFICE.split(",")[-1].strip()

            # DISTRICT ATTORNEY
            case str(x) if x.startswith("DISTRICT ATTORNEY") and x.endswith("JUDICIAL DISTRICT"):
                values['office_type'] = "DISTRICT ATTORNEY"
                values['office_district'] = OFFICE.split(",")[-1].strip()
            case str(x) if x.startswith("CRIMINAL DISTRICT ATTORNEY") and "COUNTY" in x:
                _values = OFFICE.split(",")
                values['office_type'] = "CRIMINAL DISTRICT ATTORNEY"
                if len(_values) == 1:
                    values['office_district'] = _values[0].replace("CRIMINAL DISTRICT ATTORNEY", "").strip()
            case str(x) if "DISTRICT ATTORNEY" and "COUNTY" in x:
                values['office_type'] = "DISTRICT ATTORNEY"


            # LEGISLATIVES
            case str(x) if "STATE SENATOR" in x:
                _values = OFFICE.split(" ")
                values['office_type'] = "SD"
                values['office_district'] = _values[-1].strip()
            case str(x) if "STATE REPRESENTATIVE" in x:
                _values = OFFICE.split(" ")
                values['office_type'] = "HD"
                values['office_district'] = _values[-1].strip()
            case str(x) if "U. S. REPRESENTATIVE" in x:
                _values = OFFICE.split(" ")
                values['office_type'] = "CD"
                values['office_district'] = _values[-1].strip()

            # case str(x) if "COURT OF CRIMINAL APPEALS" in x:
            #     _values = OFFICE.split(",")
            #     _office = None
            #     if "PLACE" in OFFICE:
            #         _office = "CCA " + " ".join(_values[1].split(" ")[-2:])
            #         if "CHIEF" in OFFICE:
            #             _office = "CJ" + _values[1].split(" ")[0] + " CCA" + _values[-2:]
            #     if "PRESIDING" in OFFICE:
            #         _office = "PJCCA"
            #     values['office_type'] = _office
            # case str(x) if "COURT OF APPEALS" in x:
            #     _values = OFFICE.split(",")
            #     _office = None
            #     if "PLACE" in OFFICE:
            #         if "DISTRICT" in OFFICE:
            #             _office = _values[1].split(" ")[1] + " COA" + _values[2]
            #         if "CHIEF" in OFFICE:
            #             _office = "CJ " + _values[1].split(" ")[0] + " COA" + _values[2]
            #     elif "CHIEF" in OFFICE:
            #         if "DISTRICT" in OFFICE:
            #             _office = "CJ " + _values[1].split(" ")[1] + " COA"
            #         else:
            #             _office = "CJ " + _values[1].split(" ")[0] + " COA"
            #     elif "PRESIDING" in OFFICE:
            #         _office = "PJCOA"
            #     else:
            #         _office = _values[1].split(" ")[0] + "COA"
            #     values['office_type'] = _office
            # case str(x) if "JUDICIAL DISTRICT" in x:
            #     _values = OFFICE.split(",")
            #     _split = [x.strip() for x in _values[1].split(" ")]
            #     if "DISTRICT ATTORNEY" in OFFICE:
            #         values['office_type']= DA
            #         values['office_district'] = _values[1].split(' ')[1]  # OUTPUT Ex: DA, 123TH JD
            #     else:
            #         values['office_type'] = _split[0] if len(_split) == 3 else " ".join(_split[:3]) + " JD"
            # case str(x) if "COUNTY DISTRICT ATTORNEY" in x:
            #     _values = OFFICE.split(" ")
            #     values['office_type'] = ' '.join(_values[:1]) + " DA"
            # case str(x) if "CRIMINAL DISTRICT ATTORNEY" in x:
            #     if "- UNEXPIRED TERM" in OFFICE:
            #         _values = OFFICE.split(" ")
            #         values['office_type'] = ' '.join(_values[1:-3]) + " CDA"
            #     else:
            #         _values = OFFICE.split(" ")
            #         values['office_type'] = f"CDA {' '.join(_values[-2:])}"
            # case str(x) if "MULTICOUNTY COURT AT LAW" in x:
            #     _values = OFFICE.split(" ")
            #     values['office_type'] = _values[0] + " MCL"
            # case str(x) if "RAILROAD COMMISSIONER" in x:
            #     values['office_type'] = "RRC"
            # case str(x) if "SUPREME COURT" in x:
            #     _values = OFFICE.split(",")
            #     values['office_type'] = "SCOTX" + _values[2]
            # case _:
            #     values['office_type'] = "Other"
    return values


# def set_district_number(cls, values):
#     OFFICE = values.get('office')
#     if OFFICE:
#         if "U. S. REPRESENTATIVE DISTRICT" in OFFICE:
#             values['office_district'] = int(OFFICE.split(" ")[-1])
#         elif "DISTRICT" in OFFICE:
#             _office_num = OFFICE.split("DISTRICT")[-1]
#             if _office_num.isdigit():
#                 values['office_district'] = int(_office_num)
#             else:
#                 _dist = re.findall(r'\d+', _office_num)
#                 values['office_district'] = _dist[0] if _dist else None
#         elif "PLACE" in OFFICE:
#             _office_num = f"PLACE {OFFICE.split("PLACE")[-1].strip()}"
#             values['office_district'] = _office_num
#         elif OFFICE.endswith("JUDICIAL JD"):
#             _district = OFFICE.split(" ")[0]
#             values['office_district'] = _district
#             values['office_type'] = values['office_type'].replace(_district, "").strip()
#     return values


def parse_candidate_name(self):
    name = HumanName(self.full_name)
    print(name)
    self.first_name = name.first
    self.last_name = name.last
    return self
