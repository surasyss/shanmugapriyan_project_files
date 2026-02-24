/* eslint-disable */

import React, { Component } from 'react';
import { Calendar } from 'react-native-calendars';
import {formatCalendarDate} from "../../../utils/DateFormatter";
import { View, TouchableOpacity, Text } from "react-native";
import styles from "./styles";

const XDate = require('xdate');


export default class DateRangePicker extends Component {
  constructor(props) {
    super(props);
    this.state = { isFromDatePicked: false, isToDatePicked: false, markedDates: {} };
  }

  componentDidMount() {
    this.setupInitialRange();
  }

    onDayPress = async (day) => {
      if (!this.state.isFromDatePicked || (this.state.isFromDatePicked && this.state.isToDatePicked)) {
        // this.setState({markedDates: {}});
        this.setupStartMarker(day);
      } else if (!this.state.isToDatePicked) {
        const markedDates = { ...this.state.markedDates };
        const [mMarkedDates, range] = this.setupMarkedDates(this.state.fromDate, day.dateString, markedDates);
        if (range >= 0) {
          this.setState({ isFromDatePicked: true, isToDatePicked: true, markedDates: mMarkedDates, toDate: day.dateString });
        } else {
          this.setupStartMarker(day);
        }
      }
    };

    setupStartMarker = (day) => {
      const markedDates = { [day.dateString]: { startingDay: true, color: this.props.theme.markColor, textColor: this.props.theme.markTextColor } };
      this.setState({
        isFromDatePicked: true, isToDatePicked: false, fromDate: day.dateString, markedDates, toDate: null
      });
    };

    setupMarkedDates = (fromDate, toDate, markedDates) => {
      const mFromDate = new XDate(fromDate);
      const mToDate = new XDate(toDate);
      const range = mFromDate.diffDays(mToDate);
      if (range >= 0) {
        if (range == 0) {
          markedDates = { [toDate]: { color: this.props.theme.markColor, textColor: this.props.theme.markTextColor } };
        } else {
          for (let i = 1; i <= range; i++) {
            const tempDate = mFromDate.addDays(1).toString('yyyy-MM-dd');
            if (i < range) {
              markedDates[tempDate] = { color: this.props.theme.markColor, textColor: this.props.theme.markTextColor };
            } else {
              markedDates[tempDate] = { endingDay: true, color: this.props.theme.markColor, textColor: this.props.theme.markTextColor };
            }
          }
        }
      }
      return [markedDates, range];
    }

    setupInitialRange = () => {
      if (!this.props.initialRange) return;
      const [fromDate, toDate] = this.props.initialRange;
      const markedDates = { [fromDate]: { startingDay: true, color: this.props.theme.markColor, textColor: this.props.theme.markTextColor } };
      const [mMarkedDates] = this.setupMarkedDates(fromDate, toDate, markedDates);
      this.setState({ markedDates: mMarkedDates, fromDate, toDate });
    }

    render() {
    const { fromDate, toDate } = this.state;
    const { showDatePicker } = this.props;

    let markedDates = this.state.markedDates;
    if (!markedDates || !Object.keys(markedDates).length) {
      markedDates = {};
      markedDates[formatCalendarDate()] = {
        color: '#327CF6',
        textColor: '#fff'
      };
    }

      return (
          <View style={styles.datePickerContainer}>
            <Calendar
              {...this.props}
              markingType="period"
              current={this.state.fromDate}
              markedDates={markedDates}
              onDayPress={(day) => { this.onDayPress(day); }}
            />

            <View style={styles.datePickerButtons}>
              <TouchableOpacity
                style={styles.flex_1}
                onPress={() => {
                  showDatePicker(false);
                }}
              >
                <Text style={styles.datePickerCancel}>Cancel</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.flex_1}
                disabled={!fromDate || !toDate}
                onPress={() => {
                  this.props.onSuccess(fromDate, toDate);
                  showDatePicker(false);
                }}
              >
                <Text style={[styles.datePickerSave, !fromDate || !toDate ? styles.disabled : {}]}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
      );
    }
}

DateRangePicker.defaultProps = {
  theme: { markColor: '#00adf5', markTextColor: '#ffffff' }
};
