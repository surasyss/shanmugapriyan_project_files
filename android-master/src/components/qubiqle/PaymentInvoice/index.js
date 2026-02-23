import React from 'react';
import { Text, View, TouchableOpacity } from 'react-native';
import styles from './styles';

import { toCurrencyNoSpace } from '../../../utils/StringFormatter';
import { parserInvoiceDate } from '../../../utils/DateFormatter';

export default function PaymentInvoice(props) {
  const { heading, invoice, onPress } = props;

  if (invoice) {
    const {
      id, invoice_number, date, due_date, total_amount
    } = invoice;

    return (
      <TouchableOpacity
        style={styles.mainView}
        onPress={() => {
          onPress(id);
        }}
      >
        <View style={styles.container}>
          <View style={styles.view}>
            <Text style={[styles.item, styles.left]}>{invoice_number}</Text>
          </View>

          <View
            style={styles.gap}
          />

          <View style={styles.view}>
            <Text style={[styles.item]}>{parserInvoiceDate((date))}</Text>
          </View>

          <View
            style={styles.gap}
          />

          <View style={styles.view}>
            <Text style={[styles.item]}>{parserInvoiceDate(due_date)}</Text>
          </View>

          <View
            style={styles.gap}
          />

          <View style={styles.view}>
            <Text style={[styles.item, styles.right]}>{toCurrencyNoSpace(total_amount)}</Text>
          </View>
        </View>

      </TouchableOpacity>
    );
  }

  if (heading) {
    return (
      <View style={styles.mainView}>
        <View style={styles.container}>
          <View style={styles.view}>
            <Text style={[styles.item, styles.left, styles.heading]}>Invoice No</Text>
          </View>

          <View
            style={styles.gap}
          />

          <View style={styles.view}>
            <Text style={[styles.item, styles.heading]}>Invoice Date</Text>
          </View>

          <View
            style={styles.gap}
          />

          <View style={styles.view}>
            <Text style={[styles.item, styles.heading]}>Due Date</Text>
          </View>

          <View
            style={styles.gap}
          />

          <View style={styles.view}>
            <Text style={[styles.item, styles.right, styles.heading]}>Invoice Total</Text>
          </View>
        </View>

      </View>
    );
  }
}
