import React from 'react';
import {
  View, Text, TouchableOpacity, TouchableHighlight, Image, TextInput
} from 'react-native';
import Modal from 'react-native-modal';
import ModalDropdown from 'react-native-modal-dropdown';
import { connect } from 'react-redux';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import Autocomplete from '../AutoComplete';
import styles from './styles';
import Colors from '../../../styles/Colors';
import Adapter from '../../../utils/Adapter';
import Button from '../Button';
import DateRangePicker from '../DateRangePicker';
import { formatDateRange } from '../../../utils/DateFormatter';
import Images from '../../../styles/Images';
import { loadVendors } from '../../../actions';

class Filter extends React.Component {
  constructor(props) {
    super(props);
    const {
      restaurant, date_type, company, date_range, vendor
    } = props.filters;

    this.state = {
      restaurant,
      restaurants: [],
      date_types: [
        { key: 'date', name: 'Invoice Date' },
        { key: 'created_date', name: 'Uploaded Date' },
        { key: 'exported_date', name: 'Exported Date' },
        { key: 'approved_date', name: 'Approved Date' },
        { key: 'posting_date', name: 'Posting Date' },
      ],
      date_type,
      companies: [],
      company,
      isDatePickerShowing: false,
      date_range,
      selected_date_range: null,
      vendor,
      vendor_query: vendor ? vendor.name : '',
      enableScrollViewScroll: true,
    };
  }

  async componentDidMount() {
    const restaurants = await Adapter.getRestaurants();
    const companies = await Adapter.getCompanies();
    this.setState({ restaurants, companies });
  }

    onEnableScroll= (value) => {
      this.setState({
        enableScrollViewScroll: value,
      });
    };

  showDatePicker = (isDatePickerShowing) => {
    this.setState({ isDatePickerShowing });
  };

  apply() {
    const {
      restaurant, date_type, company, date_range, vendor
    } = this.state;
    const { setFilter, openFilter } = this.props;
    const filters = {
      restaurant,
      date_type,
      company,
      date_range,
      vendor
    };
    setFilter(filters);
    openFilter(false);
  }

  clear() {
    this.setState({
      restaurant: null,
      date_type: null,
      company: null,
      date_range: null,
      vendor: null,
      vendor_query: ''
    });
  }

  renderDropDownRow(rowData) {
    return (
      <TouchableHighlight underlayColor={Colors.dividerColor}>
        <View style={styles.dropDownRow}>
          <Text style={styles.dropDownRowText}>
            {rowData.name}
          </Text>
        </View>
      </TouchableHighlight>
    );
  }

  renderDropDownDivider() {
    return (
      <View style={styles.dropDownDivider} />);
  }

  // eslint-disable-next-line consistent-return
  renderForm() {
    const {
      restaurant, restaurants, date_types, date_type, date_range, isDatePickerShowing, vendor_query
    } = this.state;
    const { vendors } = this.props;

    if (!isDatePickerShowing) {
      return (
        <View style={styles.formContainer}>
          <Text style={styles.formHeading}>DATE TYPE</Text>
          <ModalDropdown
            ref="date_type_dropdown"
            style={styles.dropDown}
            defaultIndex={0}
            dropdownStyle={styles.dropDownList}
            options={date_types}
            renderRow={this.renderDropDownRow.bind(this)}
            renderSeparator={this.renderDropDownDivider.bind(this)}
            onSelect={(idx, value) => {
              this.setState({ date_type: value });
            }}
            onDropdownWillShow={() => {
              this.refs.vendor_dropdown.blur();
              return true;
            }}
          >
            <View style={styles.dropDownButton}>
              <Text style={styles.dropDownText}>{date_type ? date_type.name : 'Invoice Date'}</Text>
              <Image
                resizeMode="contain"
                source={Images.filter_down}
                style={styles.filterRightIcon}
              />
            </View>
          </ModalDropdown>

          <Text style={styles.formHeading}>TIME RANGE</Text>
          <TouchableOpacity style={styles.dropDown} onPress={() => this.setState({ isDatePickerShowing: true })}>
            <Text style={date_range ? styles.dropDownText : styles.dropDownPlaceholder}>{date_range ? formatDateRange(date_range) : 'mm/dd/yyyy - mm/dd/yyyy'}</Text>
            <Image
              resizeMode="contain"
              source={Images.calender}
              style={styles.filterRightCalendar}
            />
          </TouchableOpacity>

          <Text style={styles.formHeading}>LOCATION</Text>
          <ModalDropdown
            ref="restaurant_dropdown"
            style={styles.dropDown}
            defaultValue="Select"
            dropdownStyle={styles.dropDownList}
            options={restaurants}
            renderRow={this.renderDropDownRow.bind(this)}
            renderSeparator={this.renderDropDownDivider.bind(this)}
            onSelect={(idx, value) => {
              this.setState({ restaurant: value });
            }}
            onDropdownWillShow={() => {
              this.refs.vendor_dropdown.blur();
              return true;
            }}
          >
            <View style={styles.dropDownButton}>
              <Text style={restaurant ? styles.dropDownText : styles.dropDownPlaceholder}>{restaurant ? restaurant.name : 'Select'}</Text>
              <Image
                resizeMode="contain"
                source={Images.filter_down}
                style={styles.filterRightIcon}
              />
            </View>
          </ModalDropdown>

          <Text style={styles.formHeading}>VENDOR</Text>
          <Autocomplete
            containerStyle={styles.dropDownAutoComplete}
            onEnableScroll={this.onEnableScroll}
            data={(this.refs.vendor_dropdown && this.refs.vendor_dropdown.isFocused()) ? vendors.data : []}
            defaultValue={vendor_query}
            renderItem={({ item }) => (
              <TouchableHighlight
                underlayColor={Colors.dividerColor}
                onPress={() => {
                  this.setState({ vendor: item });
                  this.setState({ vendor_query: item.name });
                  this.refs.vendor_dropdown.blur();
                }}
              >
                <View style={styles.dropDownRow}>
                  <Text style={styles.dropDownRowText}>
                    {item.name}
                  </Text>
                </View>
              </TouchableHighlight>
            )}
            renderTextInput={(props) => (
              <View style={styles.dropDownButton}>
                <TextInput
                  {...props}
                  style={vendor_query ? styles.dropDownAutoCompleteText : styles.dropDownPlaceholderAutoCompleteText}
                  placeholder="Select"
                  ref={(input) => { this.refs.vendor_dropdown = input; }}
                  onChangeText={(text) => {
                    this.setState({ vendor_query: text });
                    this.props.loadVendors({ query: text });
                  }}
                  onBlur={() => {
                    this.setState({ vendor_query });
                  }}
                  onFocus={async () => {
                    await this.setState({ vendor_query });
                    this.props.loadVendors({ query: vendor_query });
                  }}
                  multiline
                />
                <TouchableOpacity onPress={() => {
                  if (this.refs.vendor_dropdown) {
                    this.refs.vendor_dropdown.focus();
                  }
                }}
                >
                  <Image
                    resizeMode="contain"
                    source={Images.filter_down}
                    style={styles.filterRightIcon}
                  />
                </TouchableOpacity>
              </View>

            )}
          />

          {/* <Text style={styles.formHeading}>COMPANY</Text> */}
          {/* <ModalDropdown */}
          {/*  ref="company_dropdown" */}
          {/*  style={styles.dropDown} */}
          {/*  defaultValue="Select" */}
          {/*  dropdownStyle={styles.dropDownList} */}
          {/*  options={companies} */}
          {/*  renderRow={this.renderDropDownRow.bind(this)} */}
          {/*  renderSeparator={this.renderDropDownDivider.bind(this)} */}
          {/*  onSelect={(idx, value) => { */}
          {/*    this.setState({ company: value }); */}
          {/*  }} */}
          {/* > */}
          {/*  <View style={styles.dropDownButton}> */}
          {/*    <Text style={company ? styles.dropDownText : styles.dropDownPlaceholder}>{company ? company.name : 'Select'}</Text> */}
          {/*    <Image */}
          {/*      resizeMode="contain" */}
          {/*      source={Images.filter_down} */}
          {/*      style={styles.filterRightIcon} */}
          {/*    /> */}
          {/*  </View> */}
          {/* </ModalDropdown> */}

          <Button
            type="primary"
            title="Apply Filters"
            style={styles.applyButton}
            onPress={() => this.apply()}
          />
        </View>
      );
    }
  }

  // eslint-disable-next-line consistent-return
  renderDatePicker() {
    const { isDatePickerShowing, date_range } = this.state;
    if (isDatePickerShowing) {
      return (
        <DateRangePicker
          style={styles.datePicker}
          initialRange={date_range ? [date_range.start, date_range.end] : null}
          showDatePicker={this.showDatePicker}
          onSuccess={(start, end) => this.setState({
            date_range: { start, end }
          })}
          theme={{
            markColor: Colors.primary,
            markTextColor: Colors.white,
            monthTextColor: Colors.black,
            textMonthFontSize: 18,
            textMonthFontWeight: 'bold',
          }}
        />
      );
    }
  }

  render() {
    const { isVisible, openFilter } = this.props;

    return (
      <Modal
        hideModalContentWhileAnimating
        animationIn="slideInUp"
        animationOut="slideOutDown"
        style={styles.container}
        transparent
        isVisible={isVisible}
        backdropOpacity={0.5}
        onRequestClose={() => openFilter(false)}
      >

        <KeyboardAwareScrollView
          style={styles.scrollContainer}
          keyboardShouldPersistTaps="always"
          scrollEnabled={this.state.enableScrollViewScroll}
        >
          <View style={styles.header}>
            <TouchableOpacity style={styles.flex_1} onPress={() => openFilter(false)}>
              <Text style={styles.headerCancelButtonText}>Cancel</Text>
            </TouchableOpacity>
            <View style={styles.flex_1}>
              <Text style={styles.headerTitle}>Filters</Text>
            </View>
            <TouchableOpacity style={styles.flex_1} onPress={() => this.clear()}>
              <Text style={styles.headerClearButtonText}>Clear</Text>
            </TouchableOpacity>
          </View>
          {this.renderForm()}
          {this.renderDatePicker()}
        </KeyboardAwareScrollView>
      </Modal>
    );
  }
}

const mapStateToProps = (state) => ({
  vendors: state.vendors,
});

export default connect(
  mapStateToProps,
  { loadVendors }
)(Filter);
