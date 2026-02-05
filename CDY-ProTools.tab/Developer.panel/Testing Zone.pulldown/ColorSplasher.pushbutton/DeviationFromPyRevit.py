                        # Make surface color a few shades lighter
                        def lighten_color(color, amount):
                            r = min(color.Red + amount, 255)
                            g = min(color.Green + amount, 255)
                            b = min(color.Blue + amount, 255)
                            return DB.Color(r, g, b)
                        
                        if hasattr(wndw, "_lighten_checkbox") and wndw._lighten_checkbox.Checked:
                            surface_color = lighten_color(color, amount=30)
                        else:
                            surface_color = color

                        ogs.SetSurfaceForegroundPatternColor(surface_color)
                        ogs.SetCutForegroundPatternColor(color)
                        ogs.SetSurfaceForegroundPatternId(solid_fill_id)
                        ogs.SetCutForegroundPatternId(solid_fill_id)
                        # Get filters apply to view
                        filter_name = (
                            "S_CDY_" + sel_cat.name + "_" + sel_par.name + "_" + item.value
                        )





    def InitializeComponent(self):
        self._spr_top = Forms.Label()
        self._categories = Forms.ComboBox()
        self._search_box = Forms.TextBox()
        self._list_box1 = Forms.CheckedListBox()
        self.list_box2 = Forms.ListBox()
        self._button_set_colors = Forms.Button()
        self._button_reset_colors = Forms.Button()
        self._button_random_colors = Forms.Button()
        self._button_gradient_colors = Forms.Button()
        self._button_create_legend = Forms.Button()
        self._button_create_view_filters = Forms.Button()
        self._button_save_load_scheme = Forms.Button()
        self._txt_block2 = Forms.Label()
        self._txt_block3 = Forms.Label()
        self._txt_block4 = Forms.Label()
        self._txt_block5 = Forms.Label()
        self._search_label = Forms.Label()
        self.tooltips = Forms.ToolTip()
        self.SuspendLayout()
        self._filtered_parameters = []
        self._all_parameters = []
        # Separator Top
        self._spr_top.Anchor = (
            Forms.AnchorStyles.Top | Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        )
        self._spr_top.Location = Drawing.Point(0, 0)
        self._spr_top.Name = "spr_top"
        self._spr_top.Size = Drawing.Size(2000, 2)
        self._spr_top.BackColor = Drawing.Color.FromArgb(82, 53, 239)
        # TextBlock2
        self._txt_block2.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block2.Location = Drawing.Point(12, 2)
        self._txt_block2.Name = "txtBlock2"
        self._txt_block2.Size = Drawing.Size(120, 25)
        self._txt_block2.Text = "Category:"
        self.tooltips.SetToolTip(
            self._txt_block2, "Select a category to start coloring."
        )
        # comboBox1 Cat
        self._categories.Anchor = (
            Forms.AnchorStyles.Top
            | Forms.AnchorStyles.Bottom
            | Forms.AnchorStyles.Left
            | Forms.AnchorStyles.Right
        )
        self._categories.Location = Drawing.Point(12, 27)
        self._categories.Name = "dropDown"
        self._categories.DataSource = self.table_data
        self._categories.DisplayMember = "Key"
        self._categories.Size = Drawing.Size(310, 244)
        self._categories.DropDownWidth = 150
        self._categories.DropDownStyle = Forms.ComboBoxStyle.DropDownList
        self._categories.SelectedIndexChanged += self.update_filter
        self.tooltips.SetToolTip(
            self._categories, "Select a category to start coloring."
        )
        # TextBlock3
        self._txt_block3.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block3.Location = Drawing.Point(12, 57)
        self._txt_block3.Name = "txtBlock3"
        self._txt_block3.Size = Drawing.Size(120, 20)
        self._txt_block3.Text = "Parameters:"
        self.tooltips.SetToolTip(
            self._txt_block3, "Select a parameter to color elements based on its value."
        )
        # Search Label
        self._search_label.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._search_label.Location = Drawing.Point(12, 77)
        self._search_label.Name = "searchLabel"
        self._search_label.Size = Drawing.Size(120, 16)
        self._search_label.Text = "Search:"
        self._search_label.Font = Drawing.Font(self.Font.FontFamily, 8)
        # Search TextBox
        self._search_box.Anchor = (
            Forms.AnchorStyles.Top | Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        )
        self._search_box.Location = Drawing.Point(12, 95)
        self._search_box.Name = "searchBox"
        self._search_box.Size = Drawing.Size(310, 20)
        self._search_box.Text = ""
        self._search_box.TextChanged += self.on_search_text_changed
        self.tooltips.SetToolTip(
            self._search_box, "Type to search and filter parameters."
        )
        # checkedListBox1
        self._list_box1.Anchor = (
            Forms.AnchorStyles.Top | Forms.AnchorStyles.Left | Forms.AnchorStyles.Right
        )
        self._list_box1.FormattingEnabled = True
        self._list_box1.CheckOnClick = True
        self._list_box1.HorizontalScrollbar = True
        self._list_box1.Location = Drawing.Point(12, 122)
        self._list_box1.Name = "checkedListBox1"
        self._list_box1.DisplayMember = "Key"
        self._list_box1.Size = Drawing.Size(310, 116)
        self._list_box1.ItemCheck += self.check_item
        self.tooltips.SetToolTip(
            self._list_box1, "Select a parameter to color elements based on its value."
        )
        # TextBlock4
        self._txt_block4.Anchor = Forms.AnchorStyles.Top | Forms.AnchorStyles.Left
        self._txt_block4.Location = Drawing.Point(12, 240)
        self._txt_block4.Name = "txtBlock4"
        self._txt_block4.Size = Drawing.Size(120, 23)
        self._txt_block4.Text = "Values:"
        self.tooltips.SetToolTip(
            self._txt_block4, "Reassign colors by clicking on their value."
        )
        # TextBlock5
        self._txt_block5.Anchor = Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        self._txt_block5.Location = Drawing.Point(12, 585)
        self._txt_block5.Name = "txtBlock5"
        self._txt_block5.Size = Drawing.Size(310, 27)
        self._txt_block5.Text = "*Spaces may require a color scheme in the view."
        self._txt_block5.ForeColor = Drawing.Color.Red
        self._txt_block5.Font = Drawing.Font("Arial", 8, Drawing.FontStyle.Underline)
        self._txt_block5.Visible = False
        # checkedListBox2
        self.list_box2.Anchor = (
            Forms.AnchorStyles.Top
            | Forms.AnchorStyles.Left
            | Forms.AnchorStyles.Bottom
            | Forms.AnchorStyles.Right
        )
        
        self.list_box2.FormattingEnabled = True
        self.list_box2.HorizontalScrollbar = True
        self.list_box2.Location = Drawing.Point(12, 265)
        self.list_box2.Name = "listBox2"
        self.list_box2.DisplayMember = "Key"
        self.list_box2.DrawMode = Forms.DrawMode.OwnerDrawFixed
        self.list_box2.DrawItem += self.colour_item
        self.new_fnt = Drawing.Font(
            self.Font.FontFamily, self.Font.Size - 4, Drawing.FontStyle.Bold
        )
        g = self.list_box2.CreateGraphics()
        self.list_box2.ItemHeight = int(g.MeasureString("Sample", self.new_fnt).Height)
        self.list_box2.Size = Drawing.Size(310, 277)
        self.tooltips.SetToolTip(
            self.list_box2, "Reassign colors by clicking on their value."
        )

        table_bottom = self.list_box2.Location.Y + self.list_box2.Height

        # Lighten Surface Pattern Label
        self._lighten_label = Forms.Label()
        self._lighten_label.AutoSize = True  # automatically size width/height
        self._lighten_label.Location = Drawing.Point(12, table_bottom + 5)
        self._lighten_label.Text = "Lighten Surface Pattern:"
        self._lighten_label.Font = Drawing.Font(self.Font.FontFamily, 8)
        self.Controls.Add(self._lighten_label)

        # Lighten Surface Pattern Checkbox
        self._lighten_checkbox = Forms.CheckBox()
        self._lighten_checkbox.AutoSize = True  # auto size so it’s visible
        self._lighten_checkbox.Location = Drawing.Point(
            self._lighten_label.Location.X + self._lighten_label.PreferredWidth + 5,
            table_bottom + 8
        )  # slightly above for vertical alignment with label
        self._lighten_checkbox.Checked = True
        self.tooltips.SetToolTip(
            self._lighten_checkbox,
            "When checked, surface pattern color will be automatically lightened relative to cut color."
        )


        # set_colors_button
        self._button_set_colors.Anchor = (
            Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        )
        self._button_set_colors.Location = Drawing.Point(222, 662)
        self._button_set_colors.Name = "button_set_colors"
        self._button_set_colors.Size = Drawing.Size(100, 27)
        self._button_set_colors.Text = "Set Colors"
        self._button_set_colors.UseVisualStyleBackColor = True
        self._button_set_colors.Click += self.button_click_set_colors
        self.tooltips.SetToolTip(
            self._button_set_colors,
            "Apply the colors from each value in your Revit view.",
        )
        # reset_colors_button
        self._button_reset_colors.Anchor = (
            Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        )
        self._button_reset_colors.Location = Drawing.Point(12, 662)
        self._button_reset_colors.Name = "button_reset_colors"
        self._button_reset_colors.Size = Drawing.Size(100, 27)
        self._button_reset_colors.Text = "Reset"
        self._button_reset_colors.UseVisualStyleBackColor = True
        self._button_reset_colors.Click += self.button_click_reset
        self.tooltips.SetToolTip(
            self._button_reset_colors,
            "Reset the colors in your Revit view to its initial stage.",
        )
        # random_colors_button
        self._button_random_colors.Anchor = (
            Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        )
        self._button_random_colors.Location = Drawing.Point(167, 568)
        self._button_random_colors.Name = "button_random_colors"
        self._button_random_colors.Size = Drawing.Size(156, 25)
        self._button_random_colors.Text = "Random Colors"
        self._button_random_colors.UseVisualStyleBackColor = True
        self._button_random_colors.Click += self.button_click_random_colors
        self.tooltips.SetToolTip(
            self._button_random_colors, "Reassign new random colors to all values."
        )
        # gradient_colors_button
        self._button_gradient_colors.Anchor = (
            Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        )
        self._button_gradient_colors.Location = Drawing.Point(11, 568)
        self._button_gradient_colors.Name = "button_gradient_colors"
        self._button_gradient_colors.Size = Drawing.Size(156, 25)
        self._button_gradient_colors.Text = "Gradient Colors"
        self._button_gradient_colors.UseVisualStyleBackColor = True
        self._button_gradient_colors.Click += self.button_click_gradient_colors
        self.tooltips.SetToolTip(
            self._button_gradient_colors,
            "Based on the color of the first and last value,\nreassign gradients colors to all values.",
        )
        # create_legend_button
        self._button_create_legend.Anchor = (
            Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Left
        )
        self._button_create_legend.Location = Drawing.Point(11, 623)
        self._button_create_legend.Name = "button_create_legend"
        self._button_create_legend.Size = Drawing.Size(156, 25)
        self._button_create_legend.Text = "Create Legend"
        self._button_create_legend.UseVisualStyleBackColor = True
        self._button_create_legend.Click += self.button_click_create_legend
        self.tooltips.SetToolTip(
            self._button_create_legend,
            "Create a new legend view for all the values and their colors.",
        )
        # create_view_filters_button
        self._button_create_view_filters.Anchor = (
            Forms.AnchorStyles.Bottom | Forms.AnchorStyles.Right
        )
        self._button_create_view_filters.Location = Drawing.Point(167, 623)
        self._button_create_view_filters.Name = "button_create_view_filters"
        self._button_create_view_filters.Size = Drawing.Size(156, 25)
        self._button_create_view_filters.Text = "Create View Filters"
        self._button_create_view_filters.UseVisualStyleBackColor = True
        self._button_create_view_filters.Click += self.button_click_create_view_filters
        self.tooltips.SetToolTip(
            self._button_create_view_filters,
            "Create view filters and rules for all the values and their colors.",
        )
        # save_load_button
        self._button_save_load_scheme.Anchor = (
            Forms.AnchorStyles.Bottom
            | Forms.AnchorStyles.Right
            | Forms.AnchorStyles.Left
        )
        self._button_save_load_scheme.Location = Drawing.Point(11, 595)
        self._button_save_load_scheme.Name = "button_save_load_scheme"
        self._button_save_load_scheme.Size = Drawing.Size(312, 25)
        self._button_save_load_scheme.Text = "Save / Load Color Scheme"
        self._button_save_load_scheme.UseVisualStyleBackColor = True
        self._button_save_load_scheme.Click += self.save_load_color_scheme
        self.tooltips.SetToolTip(
            self._button_save_load_scheme,
            "Save the current color scheme or load an existing one.",
        )

        # Form
        self.TopMost = True
        self.ShowInTaskbar = False
        self.ClientSize = Drawing.Size(334, 722)
        self.MaximizeBox = 0
        self.MinimizeBox = 0
        self.CenterToScreen()
        self.FormBorderStyle = Forms.FormBorderStyle.Sizable
        self.SizeGripStyle = Forms.SizeGripStyle.Show
        self.ShowInTaskbar = True
        self.MaximizeBox = True
        self.MinimizeBox = True
        self.Controls.Add(self._spr_top)
        self.Controls.Add(self._button_set_colors)
        self.Controls.Add(self._button_reset_colors)
        self.Controls.Add(self._button_random_colors)
        self.Controls.Add(self._button_gradient_colors)
        self.Controls.Add(self._button_create_legend)
        self.Controls.Add(self._button_create_view_filters)
        self.Controls.Add(self._button_save_load_scheme)
        self.Controls.Add(self._categories)
        self.Controls.Add(self._txt_block2)
        self.Controls.Add(self._txt_block3)
        self.Controls.Add(self._search_label)
        self.Controls.Add(self._search_box)
        self.Controls.Add(self._txt_block4)
        self.Controls.Add(self._txt_block5)
        self.Controls.Add(self._list_box1)
        self.Controls.Add(self.list_box2)
        self.Controls.Add(self._lighten_checkbox)
        self.Name = "Color Elements By Parameter"
        self.Text = "Color Elements By Parameter"
        self.Closing += self.closing_event
        icon_filename = __file__.replace("script.py", "color_splasher.ico")
        if not exists(icon_filename):
            icon_filename = __file__.replace("script.py", "color_splasher.ico")
        self.Icon = Drawing.Icon(icon_filename)
        self.ResumeLayout(False)