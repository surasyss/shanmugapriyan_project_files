import React from 'react';
import { FlatList } from 'react-native';
import InvoiceEmpty from '../InvoiceEmpty';
import GlSplit from '../GlSplit';
import GlSplitUnexpanded from '../GlSplitUnexpanded';

export default function GlSplits(props) {
  let { gl_splits } = props;
  const { onPress, expandGlSplits } = props;
  if (!gl_splits) gl_splits = [];

  return (
    <FlatList
      data={gl_splits}
      renderItem={({ item, index }) => {
        if (expandGlSplits) {
          return (
            <GlSplit
              index={index}
              invoice={item}
              onPress={onPress}
            />
          );
        }
        return (
          <GlSplitUnexpanded
            index={index}
            invoice={item}
          />
        );
      }}
      ListHeaderComponent={gl_splits.length ? (
        <GlSplit
          heading
          index={0}
        />
      ) : null}
      ListEmptyComponent={(
        <InvoiceEmpty
          message="There are no Account Splits to display"
        />
        )}
      keyExtractor={(item, index) => index.toString()}
      listKey={(item, index) => index.toString()}
    />
  );
}
