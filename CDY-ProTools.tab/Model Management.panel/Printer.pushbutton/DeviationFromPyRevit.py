    def _update_filename_template(self, template, value_type, value_getter):
        finder_pattern = r'{' + value_type + r':(.*?)}'
        for param_name in re.findall(finder_pattern, template):
            param_value = value_getter(param_name)

            repl_pattern = r'{' + value_type + ':' + param_name + r'}'
            
            if param_value:
                #JW
                if param_name == 'Drawing Title 2' or param_name == 'Drawing Title 3' and param_value != "":
                    param_value = ' ' + param_value
                    #JW
                template = re.sub(repl_pattern, str(param_value), template)
            template = re.sub(repl_pattern, '', template)
            
        return template


@staticmethod
    def get_default_naming_formats():
        return [
            NamingFormat(
                name='Craddys: BS EN ISO 19650-2-2018 (+A1 2021)',
                template='{proj_number}-{sheet_param:Originator}-{sheet_param:Functional Breakdown}-{sheet_param:Spatial Breakdown}-{sheet_param:Form}-{sheet_param:Discipline}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf',
                builtin=True
            ),
            NamingFormat(
                name='Craddys: BS EN ISO 19650-2-2018',
                template='{proj_number}-{sheet_param:Originator}-{sheet_param:Volume or System}-{sheet_param:Levels and Location}-{sheet_param:Type}-{sheet_param:Role}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf',
                builtin=True
            ),
            NamingFormat(
                name='Aldi: BS1192:2007+A2:2016 (Old Template)',
                template='{proj_number}-{sheet_param:PM.Sheet.Title.Creator.Originator}-{sheet_param:PM.Sheet.Title.View.Zone}-{sheet_param:PM.Sheet.Title.View.Level}-{sheet_param:PM.Sheet.Title.View.Type}-{sheet_param:PM.Sheet.Title.Creator.Role}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf',
                builtin=True
            ),
            NamingFormat(
                name='Aldi: BS1192:2007+A2:2016 (New Template)',
                template='{proj_param:PM.Sheet.Title.Number.Project}-{sheet_param:PM.Sheet.Title.Creator.Originator}-{sheet_param:PM.Sheet.Title.View.Zone}-{sheet_param:PM.Sheet.Title.View.Level}-{sheet_param:PM.Sheet.Title.View.Type}-{sheet_param:PM.Sheet.Title.Creator.Role}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf',
                builtin=True
            ),
            NamingFormat(
                name='Morgan Sindall: BS EN ISO 19650-2-2018 (+A1 2021)',
                template='{proj_number}-{sheet_param:Originator}-{sheet_param:Functional Breakdown}-{sheet_param:Spatial Breakdown}-{sheet_param:Form}-{sheet_param:Discipline}-{sheet_param:Sheet Number}_{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}_{rev_number}.pdf',
                builtin=True
            ),
            NamingFormat(
                name='Superseded Naming Protocol',
                template='{proj_number}-{sheet_param:Sheet Number}-{rev_number}-{sheet_param:Sheet Name}{sheet_param:Drawing Title 2}{sheet_param:Drawing Title 3}.pdf',
                builtin=True
            ),
        ]