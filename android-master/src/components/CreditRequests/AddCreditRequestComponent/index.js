import React, { Component } from 'react';
import {
  Text, View, TouchableOpacity, Image, TextInput, ScrollView, Platform
} from 'react-native';
import DateTimePickerModal from 'react-native-modal-datetime-picker';
import Images from '../../../styles/Images';
import styles from './styles';
import Button from '../../qubiqle/Button';
import { formatDate } from '../../../utils/DateFormatter';
import Spinner from '../../qubiqle/Spinner';
import Colors from '../../../styles/Colors';

class AddCreditRequestComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {

    };
  }

  renderRestaurant() {
    const { data, goToRestaurantPicker } = this.props;
    const { restaurant } = data;

    return (
      <View>
        <Text style={styles.formHeading}>LOCATION</Text>
        <TouchableOpacity style={styles.inputBoxContainer} onPress={goToRestaurantPicker}>
          <Text style={restaurant ? styles.inputBoxText : styles.inputBoxPlaceholder}>{restaurant ? restaurant.name : 'Select'}</Text>
          <Image
            resizeMode="contain"
            source={Images.filter_down}
            style={styles.rightIcon}
          />
        </TouchableOpacity>
      </View>
    );
  }

  renderVendor() {
    const { data, goToVendorPicker } = this.props;
    const { vendor } = data;

    return (
      <View>
        <Text style={styles.formHeading}>VENDOR</Text>
        <TouchableOpacity style={styles.inputBoxContainer} onPress={goToVendorPicker}>
          <Text style={vendor ? styles.inputBoxText : styles.inputBoxPlaceholder}>{vendor ? vendor.name : 'Select'}</Text>
          <Image
            resizeMode="contain"
            source={Images.filter_down}
            style={styles.rightIcon}
          />
        </TouchableOpacity>
      </View>
    );
  }

  renderInvoiceNumber() {
    const { setData, data } = this.props;
    const { invoice_number } = data;

    return (
      <View>
        <Text style={styles.formHeading}>INVOICE NUMBER</Text>
        <View style={styles.inputBoxContainer}>
          <TextInput
            value={invoice_number}
            onChangeText={(text) => {
              setData('invoice_number', text);
            }}
            placeholder="Invoice Number"
            style={invoice_number ? styles.inputText : styles.inputPlaceHolder}
          />
        </View>
      </View>
    );
  }

  renderInvoiceDate() {
    const { data } = this.props;
    const { invoice_date } = data;

    return (
      <View>
        <Text style={styles.formHeading}>INVOICE DATE</Text>
        <TouchableOpacity
          style={styles.inputBoxContainer}
          onPress={() => {
            this.setState({ isDatePickerVisible: true });
          }}
        >
          <Text style={invoice_date ? styles.inputBoxText : styles.inputBoxPlaceholder}>{invoice_date || 'mm/dd/yyyy'}</Text>
          <Image
            resizeMode="contain"
            source={Images.calender}
            style={styles.rightCalendar}
          />
        </TouchableOpacity>
      </View>
    );
  }

  renderAmount() {
    const { setData, data } = this.props;
    const { total_amount } = data;

    return (
      <View>
        <Text style={styles.formHeading}>CREDIT AMOUNT</Text>
        <View style={styles.inputBoxContainer}>
          <TextInput
            keyboardType="decimal-pad"
            value={total_amount}
            onChangeText={(text) => {
              setData('total_amount', text);
            }}
            placeholder="Credit Amount"
            style={total_amount ? styles.inputText : styles.inputPlaceHolder}
          />
        </View>
      </View>
    );
  }

  renderNotes() {
    const { setData, data } = this.props;
    const { notes } = data;

    return (
      <View>
        <Text style={styles.formHeading}>NOTES</Text>
        <View style={styles.inputBoxContainer}>
          <TextInput
            value={notes}
            onChangeText={(text) => {
              setData('notes', text);
            }}
            multiline
            numberOfLines={5}
            placeholder="Notes"
            style={notes ? styles.inputText : styles.inputPlaceHolder}
          />
        </View>
      </View>
    );
  }

  renderButton() {
    const { submit } = this.props;
    return (
      <Button
        type="primary"
        title="Create Credit Request"
        style={styles.submitButton}
        onPress={() => submit()}
      />
    );
  }

  renderDatePicker() {
    const { isDatePickerVisible } = this.state;
    const { setData } = this.props;

    return (
      <DateTimePickerModal
        isVisible={isDatePickerVisible}
        mode="date"
        onConfirm={(date) => {
          setData('invoice_date', formatDate(date, 'MM/DD/YYYY'));
          this.setState({ isDatePickerVisible: false });
        }}
        onCancel={() => {
          this.setState({ isDatePickerVisible: false });
        }}
      />
    );
  }

  renderLoadingDialog() {
    const { loading } = this.props;
    return (
      <Spinner
        visible={loading}
        color={Platform.OS === 'ios' ? Colors.white : Colors.primary}
      />
    );
  }

  render() {
    return (
      <View style={styles.container}>
        <ScrollView style={styles.scrollViewContainer} showsVerticalScrollIndicator={false}>
          {this.renderRestaurant()}
          {this.renderVendor()}
          {this.renderInvoiceNumber()}
          {this.renderInvoiceDate()}
          {this.renderAmount()}
          {this.renderNotes()}
          {this.renderButton()}
          {this.renderDatePicker()}
          {this.renderLoadingDialog()}
        </ScrollView>
      </View>
    );
  }
}

export default AddCreditRequestComponent;
