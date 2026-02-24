import React from 'react';
import {
  Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';

import {
  toCurrencyNoSpace
} from '../../../utils/StringFormatter';
import { parserInvoiceDate } from '../../../utils/DateFormatter';

export default function PurchasedItemInvoice(props) {
  const {
    item, onPress, index, restaurantJson, heading
  } = props;

  if (item) {
    const {
      invoice_number, date, quantity, price, total_amount, restaurant
    } = item;

    return (
      <TouchableOpacity
        style={styles.mainView}
        onPress={() => {
          if (onPress) {
            onPress(index);
          }
        }}
      >
        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={styles.restaurant}>{restaurantJson[restaurant] ? restaurantJson[restaurant] : '--'}</Text>
            <Text style={styles.secondaryText}>{`#${invoice_number}`}</Text>
          </View>

          <View style={styles.rightView}>
            <View style={styles.valueView}>
              <Text style={styles.quantity}>
                {parserInvoiceDate(date)}
              </Text>
            </View>
            <View style={[styles.valueView, styles.flexHalf]}>
              <Text style={styles.quantity}>
                {quantity}
              </Text>
            </View>
            <View style={[styles.valueView, styles.flexHalf]}>
              <Text style={styles.quantity}>
                {toCurrencyNoSpace(price)}
              </Text>
              <Text style={[styles.secondaryText, styles.right]}>
                {toCurrencyNoSpace(total_amount)}
              </Text>
            </View>
          </View>
        </View>

      </TouchableOpacity>
    );
  }

  if (heading) {
    return (
      <View style={styles.mainView}>
        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={[styles.left, styles.heading]}>Location</Text>
          </View>

          <View style={styles.rightView}>
            <View style={styles.valueView}>
              <Text style={[styles.quantity, styles.heading]}>Date</Text>
            </View>

            <View style={styles.valueView}>
              <Text style={[styles.quantity, styles.heading]}>Qty</Text>
            </View>

            <View style={styles.valueView}>
              <Text style={[styles.quantity, styles.heading]}>Price</Text>
            </View>
          </View>
        </View>
      </View>
    );
  }
}
