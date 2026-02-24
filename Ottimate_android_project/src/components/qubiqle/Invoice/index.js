import React from 'react';
import {
  Image, Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';

import { parserInvoiceDate } from '../../../utils/DateFormatter';
import Images from '../../../styles/Images';
import { toCurrency } from '../../../utils/StringFormatter';

export default function Invoice(props) {
  const { invoice, onPress, index } = props;

  if (invoice) {
    let vendor_name = '';
    const {
      vendor_obj, date, total_amount, is_vendor_supplied_invoice, invoice_number, is_flagged
    } = invoice;
    if (vendor_obj) vendor_name = vendor_obj.name;

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
            <Text style={[styles.vendorName]}>{vendor_name || 'No Vendor Info'}</Text>
          </View>

          <View style={styles.rightView}>
            {is_flagged
              ? (
                <Image
                  resizeMode="contain"
                  source={Images.flag}
                  style={[styles.flag]}
                />
              )
              : null}

            {is_vendor_supplied_invoice
              ? (
                <Image
                  resizeMode="contain"
                  source={Images.mail_icon}
                  style={styles.email}
                />
              )
              : null}
          </View>
        </View>

        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={invoice_number ? styles.secondaryText : styles.missingSecondaryText}>
              {
                invoice_number ? `${invoice_number}     ${parserInvoiceDate(date)}`
                  : 'Invoice #'
              }
            </Text>
          </View>

          <View style={styles.rightView}>
            <Text style={styles.amount}>
              {toCurrency(total_amount)}
            </Text>
          </View>
        </View>

      </TouchableOpacity>
    );
  }
}
