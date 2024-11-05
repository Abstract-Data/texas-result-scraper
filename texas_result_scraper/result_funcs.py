from nameparser import HumanName


def set_office_type(self):
    match self.office:
        case "PRESIDENT":
            self.office_type = "POTUS"
        case "U. S. SENATOR":
            self.office_type = "US Senate"
        case "GOVERNOR":
            self.office_type = "Governor"
        case "STATE SENATOR":
            self.office_type = "SD"
        case "STATE REPRESENTATIVE":
            self.office_type = "HD"
        case "U. S. REPRESENTATIVE":
            self.office_type = "CD"
        case "STATE BOARD OF EDUCATION":
            self.office_type = "SBOE"
        case "COURT OF CRIMINAL APPEALS":
            _values = self.office.split(",")
            _office = None
            if "PLACE" in self.office:
                _office = "CCA " + " ".join(_values[1].split(" ")[-2:])
                if "CHIEF" in self.office:
                    _office = "CJ" + _values[1].split(" ")[0] + " CCA" + _values[-2:]
            if "PRESIDING" in self.office:
                _office = "PJCCA"
            self.office_type = _office
        case "COURT OF APPEALS":
            _values = self.office.split(",")
            _office = None
            if "PLACE" in self.office:
                if "DISTRICT" in self.office:
                    _office = _values[1].split(" ")[1] + " COA" + _values[2]
                if "CHIEF" in self.office:
                    _office = "CJ " + _values[1].split(" ")[0] + " COA" + _values[2]
            elif "CHIEF" in self.office:
                if "DISTRICT" in self.office:
                    _office = "CJ " + _values[1].split(" ")[1] + " COA"
                else:
                    _office = "CJ " + _values[1].split(" ")[0] + " COA"
            elif "PRESIDING" in self.office:
                _office = "PJCOA"
            else:
                _office = _values[1].split(" ")[0] + "COA"
            self.office_type = _office
        case "JUDICIAL DISTRICT":
            _values = self.office.split(",")
            _split = [x.strip() for x in _values[1].split(" ")]
            if "DISTRICT ATTORNEY" in self.office:
                self.office_type = f"DA, {_values[1].split(' ')[1]} JD"  # OUTPUT Ex: DA, 123TH JD
            else:
                self.office_type = _split[0] if len(_split) == 3 else " ".join(_split[:3]) + " JD"
        case "COUNTY DISTRICT ATTORNEY":
            _values = self.office.split(" ")
            self.office_type = ' '.join(_values[:1]) + " DA"
        case "CRIMINAL DISTRICT ATTORNEY":
            if "- UNEXPIRED TERM" in self.office:
                _values = self.office.split(" ")
                self.office_type = ' '.join(_values[1:-3]) + " CDA"
            else:
                _values = self.office.split(" ")
                self.office_type = f"CDA {' '.join(_values[-2:])}"
        case "MULTICOUNTY COURT AT LAW":
            _values = self.office.split(" ")
            self.office_type = _values[0] + " MCL"
        case "RAILROAD COMMISSIONER":
            self.office_type = "RRC"
        case "SUPREME COURT":
            _values = self.office.split(",")
            self.office_type = "SCOTX" + _values[2]
        case _:
            self.office_type = "Other"
    return self


def set_district_number(self):
    if "DISTRICT" in self.office:
        _office_num = self.office.split(" ")[-1]
        if _office_num.isdigit():
            self.office_district_number = int(_office_num)
    return self


def parse_candidate_name(self):
    name = HumanName(self.full_name)
    print(name)
    self.first_name = name.first
    self.last_name = name.last
    return self
