import React from 'react';
import {
  Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';

import { parserInvoiceDate } from '../../../utils/DateFormatter';
import { toCurrency } from '../../../utils/StringFormatter';
import Label from '../Label';

export const renderPaymentType = (payment) => {
  const {
    is_ach_payment, is_first_time, payment_type
  } = payment;

  if (is_ach_payment) {
    return (
      <Label
        title="ACH"
        style={styles.ach_flag}
      />
    );
  }

  if (is_first_time) {
    return (
      <Label
        title="New Address"
        style={styles.newAddress}
      />
    );
  }

  if (payment_type && payment_type === 'vcard') {
    return (
      <Label
        title="VCARD"
        style={styles.vcard}
      />
    );
  }
  return null;
};

export const renderStatus = (status) => {
  if (!status) status = '';
  status = status.toLowerCase();
  if (status === 'sent') {
    return (
      <Label
        title="Sent"
        style={styles.sent}
      />
    );
  }

  if (status === 'paid') {
    return (
      <Label
        title="Paid"
        style={styles.paid}
      />
    );
  }

  if (status === 'delivered') {
    return (
      <Label
        title="Delivered"
        style={styles.delivered}
      />
    );
  }

  if (status === 'scheduled') {
    return (
      <Label
        title="Scheduled"
        style={styles.scheduled}
      />
    );
  }

  if (status === 'pending approval') {
    return (
      <Label
        title="Pending Approval"
        style={styles.pendingApproval}
      />
    );
  }

  if (status === 'canceled') {
    return (
      <Label
        title="Canceled"
        style={styles.cancelled}
      />
    );
  }

  return null;
};

export default function Payment(props) {
  const {
    payment, onPress, index, showPaymentType, showStatus
  } = props;

  if (payment) {
    const {
      vendor_name, scheduled_date, total_amount, id, status
    } = payment;

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
            { showPaymentType ? renderPaymentType(payment) : null }
            { showStatus ? renderStatus(status) : null }
          </View>
        </View>

        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={styles.secondaryText}>
              CR
              {id}
              {'    '}
              {scheduled_date ? parserInvoiceDate(scheduled_date) : '----'}
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
