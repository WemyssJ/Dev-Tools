using System.Windows;
using System.Windows.Controls;

namespace PyRevitXamlDesigner {
    public partial class MainWindow : Window {
        public MainWindow() {
            InitializeComponent();
        }
        private void print_sheets(object sender, RoutedEventArgs e) { }
        private void doclist_changed(object sender, SelectionChangedEventArgs e) { }
        private void sheetlist_changed(object sender, SelectionChangedEventArgs e) { }
        private void options_changed(object sender, RoutedEventArgs e) { }
        private void printers_changed(object sender, SelectionChangedEventArgs e) { }
        private void rest_index(object sender, RoutedEventArgs e) { }
        private void validate_index_start(object sender, RoutedEventArgs e) { }
        private void find_empty_sheets_clicked(object sender, RoutedEventArgs e) { }
        private void edit_formats(object sender, RoutedEventArgs e) { }
        private void set_sheet_printsettings(object sender, RoutedEventArgs e) { }
        private void sheet_selection_changed(object sender, SelectionChangedEventArgs e) { }
        private void copy_filenames(object sender, RoutedEventArgs e) { }
        private void handle_url_click(object sender, RoutedEventArgs e) { }
    }
}
